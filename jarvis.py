import speech_recognition as sr
import simpleaudio as sa

from send_email import send_email
from ai_parser import (
    parse_email_command,
    load_contacts,
    save_new_contact,
    replace_contact_name
)
from gmail_contacts import extract_contacts_from_sent_and_inbox, merge_with_existing_contacts


def play_sound(file):
    try:
        wave_obj = sa.WaveObject.from_wave_file(file)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print("❌ Failed to play sound:", e)


def listen_until_wake_word(wake_word="hey jarvis", sound_path="ding.wav"):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎙️ Passive mode: say 'Hey Jarvis' to activate...")

    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            phrase = recognizer.recognize_google(audio).lower()
            print(f"🗣️ Heard: {phrase}")

            if "exit" in phrase or "quit" in phrase:
                print("👋 Exiting passive mode...")
                return None

            if wake_word in phrase:
                index = phrase.index(wake_word)
                after = phrase[index + len(wake_word):].strip()
                if sound_path:
                    play_sound(sound_path)
                return after
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            break


def listen_to_voice():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎙️ Listening for a voice command...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        command = recognizer.recognize_google(audio)
        print(f"You said: {command}")
        return command
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return None


# Sync Gmail contacts on startup
new_contacts = extract_contacts_from_sent_and_inbox(max_emails=20)
merge_with_existing_contacts(new_contacts)


def parse_command(command):
    if "email" in command.lower():
        contacts = load_contacts()
        email_data = parse_email_command(command)

        if not email_data:
            print("Could not understand the email command.")
            return

        email_data = replace_contact_name(email_data, contacts)

        if not email_data["to"]:
            name = input("Enter the contact name: ").lower()
            email = input("Enter their email address: ")
            save_new_contact(name, email)
            email_data["to"] = email

        print("\nEmail Preview:")
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
            print("Email canceled.")
    else:
        print("Command not recognized yet.")


if __name__ == "__main__":
    print("Jarvis is ready.")
    while True:
        mode = input("Mode? (t = type, v = voice-once, w = wake-word, q = quit): ").strip().lower()

        if mode == "q":
            break
        elif mode == "t":
            cmd = input("You: ")
            parse_command(cmd)
        elif mode == "v":
            spoken = listen_to_voice()
            if spoken:
                parse_command(spoken)
        elif mode == "w":
            print("🛌 Passive wake mode active. Say 'Hey Jarvis' anytime.")
            while True:
                cmd = listen_until_wake_word()
                if cmd:
                    parse_command(cmd)
