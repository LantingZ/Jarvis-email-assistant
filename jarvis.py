from send_email import send_email
from ai_parser import (
    parse_email_command,
    load_contacts,
    save_new_contact,
    replace_contact_name
)
from gmail_contacts import extract_contacts_from_sent_and_inbox, merge_with_existing_contacts

import speech_recognition as sr

def listen_to_voice():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎙️ Listening for a voice command...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        command = recognizer.recognize_google(audio)
        print(f"🗣️ You said: {command}")
        return command
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")
        return None
    
# Sync Gmail contacts on startup
new_contacts = extract_contacts_from_sent_and_inbox(max_emails=20)
merge_with_existing_contacts(new_contacts)

def parse_command(command):
    if "email" in command.lower():
        contacts = load_contacts()
        email_data = parse_email_command(command)

        if not email_data:
            print("❌ Could not understand the email command.")
            return

        email_data = replace_contact_name(email_data, contacts)

        if not email_data["to"]:
            name = input("Enter the contact name: ").lower()
            email = input("Enter their email address: ")
            save_new_contact(name, email)
            email_data["to"] = email

        print("\n📤 Email Preview:")
        print(f"To: {email_data['to']}")
        print(f"Subject: {email_data['subject']}")
        print(f"Body:\n{email_data['body']}\n")

        confirm = input("Send this email? (yes/no): ").strip().lower()
        if confirm == "yes":
            send_email(
                to=email_data['to'],
                subject=email_data['subject'],
                body=email_data['body']
            )
        else:
            print("❌ Email canceled.")
    else:
        print("🤖 Command not recognized yet.")

if __name__ == "__main__":
    print("Jarvis is listening...")
    while True:
        mode = input("Type or say? (t = type, v = voice, q = quit): ").strip().lower()

        if mode == "q":
            break
        elif mode == "t":
            cmd = input("You: ")
            parse_command(cmd)
        elif mode == "v":
            spoken = listen_to_voice()
            if spoken:
                parse_command(spoken)
        else:
            print("❓ Unknown mode. Use 't' to type, 'v' to speak, or 'q' to quit.")
