# TOS_final_project

Environment:
execute on virtual environment

python -m venv venv
.\venv\Scripts\Activate.ps1

if running scripts is disabled

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1

Requirement:

pip install flask, 

sign up with HF , create access token, go to https://huggingface.co/google/embeddinggemma-300m and press Acknowlege license

for vector dataset:

python -X utf8 -m pip install -r requirements.txt


setx LLM_API_KEY "YOUR_API_KEY"
setx GOOGLE_API_KEY "YOUR_API_KEY"
setx HUGGING_FACE_TOKEN "YOUR_HF_TOKEN"


