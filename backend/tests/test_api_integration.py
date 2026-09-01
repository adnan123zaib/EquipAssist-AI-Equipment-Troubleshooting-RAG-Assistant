import time

def wait_indexed(client,manual_id):
    for _ in range(80):
        m=client.get(f'/api/v1/manuals/{manual_id}').json()
        if m['status'] in ('indexed','failed'): return m
        time.sleep(.05)
    return m

def ensure_manual(client,sample_pdf):
    current=client.get('/api/v1/manuals').json()
    if current: return current[0]
    r=client.post('/api/v1/manuals/upload',files={'files':('PX-200_manual.pdf',sample_pdf.read_bytes(),'application/pdf')},data={'equipment_name':'PX-200 Industrial Hydraulic Pump Controller','manufacturer':'Northstar','model_number':'PX-200','version':'1.4'})
    return wait_indexed(client,r.json()[0]['id'])

def test_health(client): assert client.get('/api/v1/health').json()['status']=='ok'

def test_chat_success_exact_retrieval_and_citations(client,sample_pdf):
    m=ensure_manual(client,sample_pdf); m=wait_indexed(client,m['id']); assert m['status']=='indexed'
    r=client.post('/api/v1/chat/query',json={'question':'What does E05 mean and how should I troubleshoot it?','manual_ids':[m['id']]}); assert r.status_code==200
    body=r.json(); assert body['citations']; assert any('E05' in c['excerpt'] for c in body['citations']); assert body['troubleshooting_steps']; assert body['confidence']['components']['exact_identifier_match']==1

def test_weak_evidence_refusal(client,sample_pdf):
    m=ensure_manual(client,sample_pdf); r=client.post('/api/v1/chat/query',json={'question':'How do I repair quantum telemetry code AL-9999?','manual_ids':[m['id']]}); assert 'could not find enough' in r.json()['answer'].lower()

def test_manual_delete_sql_and_vector(client,sample_pdf):
    m=ensure_manual(client,sample_pdf); from app.api.deps import services
    _,_,store,_=services(); assert store.count_manual(m['id'])>0
    assert client.delete(f"/api/v1/manuals/{m['id']}").status_code==204; assert store.count_manual(m['id'])==0; assert client.get(f"/api/v1/manuals/{m['id']}").status_code==404



def test_query_without_manual_ids_is_scoped_to_current_user(client, sample_pdf):
    from app.api.deps import services

    # The vector layer must require the owner metadata whenever manual_ids is omitted.
    _, _, store, _ = services()
    assert store._where(owner_user_id="owner-a") == {"owner_user_id": "owner-a"}
    assert store._where(["m1", "m2"], "owner-a") == {
        "$and": [{"owner_user_id": "owner-a"}, {"manual_id": {"$in": ["m1", "m2"]}}]
    }
