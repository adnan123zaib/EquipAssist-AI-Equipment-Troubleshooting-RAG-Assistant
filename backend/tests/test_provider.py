import pytest
from app.services.generation.providers import LocalProvider

@pytest.mark.asyncio
async def test_local_provider_is_deterministic_and_free():
    r=await LocalProvider().generate('QUESTION E05\nEVIDENCE:\nE05 means motor overtemperature.'); assert 'steps' in r and 'E05' in r

@pytest.mark.asyncio
async def test_provider_failure_is_caught_by_workflow(monkeypatch):
    class Broken:
        async def generate(self,prompt): raise RuntimeError('provider unavailable')
    from app.agents.workflow import TroubleshootingGraph
    from app.services.retrieval.hybrid import RetrievedChunk
    class Retriever:
        async def search(self,*args,**kwargs): return [RetrievedChunk('1','E05 fault',{'manual_id':'m','manual_filename':'m.pdf','page_number':1,'section_title':'Fault'},.9,.9,True),RetrievedChunk('2','E05 safety',{'manual_id':'m','manual_filename':'m.pdf','page_number':2,'section_title':'Safety'},.8,.8,True)]
    result=await TroubleshootingGraph(Retriever(),Broken()).run(question='E05?',manual_ids=[],equipment_model='PX-200',top_k=6); assert 'qualified technician' in result['answer']



def test_generation_provider_honors_local_configuration():
    from app.core.config import Settings
    from app.services.generation.providers import LocalProvider, generation_provider
    settings = Settings(app_env="test", llm_provider="local")
    assert isinstance(generation_provider(settings), LocalProvider)


@pytest.mark.asyncio
async def test_malformed_provider_json_is_rejected_without_response_shape_error():
    class Malformed:
        async def generate(self, prompt):
            return '{"steps":"not-a-list","meaning":123}'

    from app.agents.workflow import TroubleshootingGraph
    from app.services.retrieval.hybrid import RetrievedChunk

    class Retriever:
        async def search(self, *args, **kwargs):
            return [
                RetrievedChunk("1", "E05 fault", {"manual_id": "m", "manual_filename": "m.pdf", "page_number": 1, "section_title": "Fault"}, .9, .9, True),
                RetrievedChunk("2", "E05 safety", {"manual_id": "m", "manual_filename": "m.pdf", "page_number": 2, "section_title": "Safety"}, .8, .8, True),
            ]

    result = await TroubleshootingGraph(Retriever(), Malformed()).run(
        question="E05?", manual_ids=[], equipment_model="PX-200", top_k=6
    )
    assert isinstance(result["troubleshooting_steps"], list)
    assert "validated grounded response" in result["answer"]
