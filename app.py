import time
import sys
import signal
import multiprocessing
import pyperclip
import subprocess
from smartcard.System import readers
from smartcard.util import toHexString

POLL_INTERVAL = 1  # Time to wait between scans (seconds)
PROCESS_TIMEOUT = 10  # Kill NFC process if it runs longer than this

# Handle Ctrl+C cleanly
def signal_handler(sig, frame):
    print("\n🔴 Stopping NFC scanner...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def paste_with_applescript():
    """Uses AppleScript to paste and press Enter instantly."""
    applescript = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.05
        keystroke return
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])

def nfc_reader_process():
    """Runs NFC scanning in a separate process to prevent deadlocks."""
    while True:
        try:
            r = readers()
            if not r:
                print("❌ No NFC reader found.")
                time.sleep(POLL_INTERVAL)
                continue

            reader = r[0]
            connection = reader.createConnection()
            connection.connect()
            print("✅ Card detected! Reading full data...")

            full_data = ""

            # Read all user data pages (Page 4 to Page 15, 48 bytes total)
            for page in range(4, 16, 4):  # Read in 16-byte chunks
                READ_CMD = [0xFF, 0xB0, 0x00, page, 0x10]
                response, sw1, sw2 = connection.transmit(READ_CMD)

                if sw1 == 0x90:
                    full_data += "".join(chr(b) for b in response if 32 <= b <= 126)

            if full_data.strip():
                full_data = full_data.lstrip(")%U")  # Remove 'U' prefix if present
                full_data = "https://" + full_data
                print(f"🖋️ Pasting: {full_data}")

                # **FASTEST METHOD** → Copy to clipboard and paste + press Enter instantly
                pyperclip.copy(full_data)
                time.sleep(0.1)  # Ensure clipboard updates
                paste_with_applescript()  # Use AppleScript to paste and press Enter

            else:
                print("⚠️ No valid data read. Skipping.")

        except Exception as e:
            print(f"⚠️ Error: {e} — Skipping scan.")

        time.sleep(POLL_INTERVAL)  # Prevent excessive polling

def monitor_nfc_process():
    """Monitors the NFC process and restarts it if it freezes."""
    while True:
        print("🔄 Starting NFC reader process...")
        p = multiprocessing.Process(target=nfc_reader_process)
        p.start()
        p.join(PROCESS_TIMEOUT)  # Wait for the process to complete or time out

        if p.is_alive():
            print("⚠️ NFC process frozen! Restarting...")
            p.terminate()
            p.join()
        else:
            print("🔁 NFC process completed. Restarting in 1 second...")

        time.sleep(1)

if __name__ == "__main__":
    print("🎯 NFC Scanner Active. Tap a card to read...")
    monitor_nfc_process()