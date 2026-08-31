import json
import requests

# Read the script
with open("/home/holk/Documents/proyectos/podcast/podcast with VRAM nvidia/Guiones/historias_de_crimenes_jonbenet_ramsey_script_v2.txt", "r") as f:
    script_text = f.read()

# Auth token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc4ODY3NDg4OX0.dic1vN3lRn41rFbcUTCxpuF695DAQW8byg9jg-DnfDo"

# Episode data
episode_data = {
    "title": "JonBenét Ramsey — La casa, la nota y el misterio que nunca terminó",
    "type": "podcast",
    "source_text": script_text,
    "voice_id": "clone:alejandra",
    "target_duration_minutes": 18
}

# Create episode
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.podcash.app.moonsbow.com/api/episodes",
    headers=headers,
    json=episode_data
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")