#!/usr/bin/env python3
"""
Interactive SMS Verification for moomoo OpenD
This script helps complete the phone verification process
"""

import subprocess
import time
import sys
import select
import threading
from pexpect import pxssh, spawn, TIMEOUT, EOF

def run_opend_with_verification():
    """Run OpenD and handle SMS verification interactively"""

    print("🔐 Starting OpenD with SMS Verification Support")
    print("=" * 60)

    # Ask user for the SMS code upfront
    sms_code = input("\n📱 Please enter the SMS verification code you received: ").strip()

    if not sms_code:
        print("❌ No SMS code provided. Exiting.")
        return False

    print(f"✅ SMS code received: {sms_code}")
    print("\n🚀 Starting OpenD in Alice container...")

    try:
        # Use docker exec to run OpenD in the container
        cmd = ['docker', 'exec', '-i', 'moomoo-user-alice', '/app/opend/OpenD']

        # Start the process
        process = spawn(' '.join(cmd))
        process.logfile_read = sys.stdout.buffer

        print("⏳ Waiting for OpenD to start and prompt for verification...")

        # Wait for verification prompt (timeout after 30 seconds)
        index = process.expect([
            'verification',  # Common verification prompt
            'code',          # Code prompt
            'SMS',           # SMS prompt
            '验证',          # Chinese verification
            TIMEOUT,
            EOF
        ], timeout=30)

        if index < 4:  # Found a verification prompt
            print(f"\n✅ Verification prompt detected!")
            print(f"📝 Sending SMS code: {sms_code}")

            # Send the SMS code
            process.sendline(sms_code)

            # Wait for success confirmation
            success_index = process.expect([
                'success',
                'connected',
                'authenticated',
                '成功',  # Chinese success
                'failed',
                'error',
                TIMEOUT
            ], timeout=10)

            if success_index < 4:  # Success indicators
                print("🎉 SMS verification successful!")
                print("✅ OpenD authenticated and ready for trading data!")

                # Let it run for a few seconds to establish connection
                time.sleep(5)

                return True
            else:
                print("❌ SMS verification failed or timed out")
                return False

        else:  # Timeout or EOF
            print("⚠️ No verification prompt detected within 30 seconds")
            print("📋 OpenD output:")
            if process.before:
                print(process.before.decode('utf-8', errors='ignore'))
            return False

    except Exception as e:
        print(f"❌ Error during SMS verification: {e}")
        return False
    finally:
        try:
            process.close()
        except:
            pass

def check_container_status():
    """Check if the container and OpenD are ready"""
    print("🔍 Checking container status...")

    try:
        # Check if container is running
        result = subprocess.run(['docker', 'exec', 'moomoo-user-alice', 'ps', 'aux'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print("✅ Container is running")
            return True
        else:
            print("❌ Container is not accessible")
            return False

    except Exception as e:
        print(f"❌ Error checking container: {e}")
        return False

if __name__ == "__main__":
    print("moomoo OpenD SMS Verification Helper")
    print("This script will help you complete the SMS verification for OpenD")
    print()

    # Check container status first
    if not check_container_status():
        print("Please ensure the moomoo-user-alice container is running")
        sys.exit(1)

    # Run the verification process
    success = run_opend_with_verification()

    if success:
        print("\n🎉 SMS Verification Complete!")
        print("Your OpenD binary is now authenticated and ready for live trading data.")
        print("You can now test the platform at http://localhost/")
        sys.exit(0)
    else:
        print("\n❌ SMS Verification Failed")
        print("Please try running the verification process manually:")
        print("1. docker exec -it moomoo-user-alice /bin/bash")
        print("2. cd /app/opend")
        print("3. ./OpenD")
        print("4. Enter your SMS code when prompted")
        sys.exit(1)