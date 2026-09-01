# PX-200 Industrial Hydraulic Pump Controller

Manufacturer: Northstar Industrial Controls (fictional)  
Model: PX-200  
Manual version: 1.4

## 1. Safety Instructions

Only trained personnel may service the PX-200. Before opening an electrical enclosure or inspecting the motor, stop the controller, disconnect the main supply, apply lockout/tagout, verify zero voltage with a rated tester, and wait five minutes for stored electrical energy to discharge. Before loosening a hydraulic connection, stop the pump, close the isolation valves, discharge accumulator pressure, and verify that the pressure gauge reads zero. Never bypass an interlock, guard, emergency stop, circuit protection device, temperature switch, or pressure relief valve. Wear eye protection, gloves suitable for hydraulic oil, and safety footwear. A qualified technician is required for exposed conductors, damaged wiring, repeated protection trips, internal leakage, or pressure that cannot be safely released.

## 2. System Overview

The PX-200 controls a three-phase hydraulic pump motor, cooling fan, pressure transducer, inlet-voltage monitor, and safety interlocks. The normal operating pressure range is 110–145 bar when configured for the standard Northstar test rig. Always use the equipment-specific nameplate and commissioning sheet if the controller is installed on another machine. The display reports operating state, measured pressure, motor temperature, and active fault code.

## 3. Installation

Mount the controller upright with 150 mm of clear ventilation space. Confirm that the supply and protective earth match the controller nameplate. Connect the pressure sensor only to the designated sensor terminal. Hydraulic hoses must be rated above the machine relief setting. After wiring, inspect terminal torque, guards, hose routing, fluid level, and valve positions before energizing.

## 4. Startup Procedure

Confirm guards and panel covers are installed. Verify hydraulic fluid is at the marked level and the inlet valve is fully open. Release the emergency stop, energize the isolator, and press START. The controller performs a three-second sensor check. Observe pressure rise for 30 seconds. Stop immediately if there is a leak, unusual noise, unstable pressure, smoke, or a repeated fault.

## 5. Preventive Maintenance

Weekly: inspect for leaks, blocked ventilation, abnormal noise, loose external connectors, and fluid contamination. Monthly: clean the cooling grille with power isolated, inspect the fan, check the fluid level, and review the fault log. Every six months: a qualified technician must verify protective earth, terminal condition, pressure-sensor accuracy, relief-valve setting, and motor current against the commissioning sheet.

## 6. Troubleshooting Table

### Motor starts then stops

Record the displayed fault code before resetting. Check that the emergency stop and guards remain closed, inlet voltage remains stable, cooling airflow is unobstructed, and hydraulic demand is not above the commissioned limit. Do not repeatedly reset a protection trip. If no code is displayed, isolate power and have a qualified technician inspect the contactor feedback and motor protection circuit.

### Low hydraulic pressure symptom

Stop the pump if pressure falls suddenly or a leak is visible. Isolate power and release hydraulic pressure. Inspect the reservoir level, inlet isolation valve, suction hose for collapse or leakage, inlet strainer, filter restriction indicator, and visible pipework. After correcting a documented external condition, restore guards and valves, start the controller, and verify that pressure stabilizes within the commissioned range. Persistent low pressure may indicate pump wear, an incorrectly set relief valve, internal leakage, or a sensor problem; these conditions require a qualified hydraulic technician.

## 7. Error Codes

### E01: Low Input Voltage

E01 means input voltage fell below the configured safe threshold. Stop the unit. A qualified person must measure supply voltage at the approved test point and compare it with the nameplate range. Inspect upstream supply connections only after lockout/tagout. Do not bridge the voltage monitor. Restart only after the stable supply is restored and verify that E01 does not return.

### E05: Motor Overtemperature

E05 means the motor temperature input exceeded the configured trip threshold. Allow the motor to cool with the equipment stopped. Isolate the main supply and apply lockout/tagout before inspection. Check the cooling grille for blockage, confirm the cooling fan turns freely and its connector is secure, inspect for excessive hydraulic load, and check that the motor is not being started too frequently. Restore all guards before restarting. Run the pump unloaded for two minutes, then at normal demand while monitoring temperature. If E05 returns, the fan is damaged, wiring is heat-damaged, or the motor smells burnt, stop and contact a qualified technician. Do not bypass the temperature input.

### E12: Low Hydraulic Pressure

E12 means measured hydraulic pressure remained below the configured minimum for ten seconds after startup. Stop the pump, isolate electrical power, close isolation valves, release stored pressure, and verify zero pressure. Check reservoir fluid level, inlet valve position, suction hose condition, strainer blockage, filter restriction, external leakage, and pump rotation. Restore pressure containment and guards before restarting. Verify that pressure rises steadily and remains above the configured minimum for at least 30 seconds. If E12 remains, a qualified technician must test the pump, relief valve, and transducer.

### F03: Pressure Sensor Fault

F03 means the pressure-sensor signal is outside its valid electrical range or is unstable. Do not assume that hydraulic pressure is zero. Stop the pump and release stored hydraulic pressure using the approved procedure. With power locked out, inspect the sensor connector and cable for looseness, contamination, crushing, or heat damage. Do not apply an external test voltage to the input. A qualified technician must compare sensor output with a calibrated mechanical gauge and replace or recalibrate the sensor if required.

## 8. Emergency Shutdown Procedure

Use emergency shutdown immediately for an uncontrolled hydraulic leak, burst hose, smoke, fire, electrical arcing, severe vibration, unexpected machine movement, failed guard or interlock, pressure above the safe limit, or any danger to personnel. Press the emergency-stop button, keep clear of moving parts and escaping fluid, and switch off the main isolator only if it is safe to approach. Warn nearby personnel and restrict access. Do not touch a suspected high-pressure pinhole leak. Call emergency services for fire or injury. The equipment must remain locked out until a qualified technician identifies the cause, repairs the system, inspects affected safety devices, and authorizes a controlled restart.

## 9. Contact a Technician

Contact a qualified technician when a fault returns after one documented troubleshooting cycle; wiring, insulation, motor windings, pump internals, relief settings, or safety devices require inspection; pressure cannot be fully released; a source conflict exists; the controller model or commissioning limits are uncertain; or any instruction would require bypassing a protection device. Provide the model, serial number, exact fault code, operating state, measured pressure, and events immediately before the fault.

