@echo off
cd /d "%~dp0"
python -m dvsa_appointment_setter.cli --config config.example.json
