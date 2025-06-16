# ai_parser.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_contacts():
    with open("contacts.json", "r") as f:
        return json.load(f)

def save_new_contact(name, email):
    with open("contacts.json", "r+") as f:
        contacts = json.load(f)
        contacts[name.lower()] = email
        f.seek(0)
        json.dump(contacts, f, indent=2)
        f.truncate()

def replace_contact_name(email_data, contacts):
    input_name = email_data["to"].lower()

    if input_name in contacts:
        email_data["to"] = contacts[input_name]
        return email_data

    #Try fuzzy AI match with GPT
    matched_name = fuzzy_match_contact(input_name, contacts)
    if matched_name:
        email_data["to"] = contacts[matched_name]
    else:
        print(f"❌ No contact match found for '{input_name}'.")

    return email_data

def fuzzy_match_contact(input_name, contacts):
    try:
        prompt = (
            "You are a helpful assistant. Given a list of contact names and a partial or short name, "
            "return the most likely full contact name that matches. "
            "If there's no clear match, return null.\n\n"
            f"Contacts: {list(contacts.keys())}\n"
            f"Input: {input_name}\n"
            "Respond with JSON: {\"match\": \"<name>\"} or {\"match\": null}"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Match contact names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()
        match_json = json.loads(content)
        return match_json.get("match")
    except Exception as e:
        print("❌ AI contact matching failed:", e)
        return None


def parse_email_command(prompt):
    system_msg = (
        "You are an assistant that turns natural language into structured email data. "
        "Return a JSON object with 'to', 'subject', and 'body'. "
        "Guess the subject and body if needed, but assume the user already knows the recipient by name."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        print("❌ Failed to parse response:", e)
        return None
