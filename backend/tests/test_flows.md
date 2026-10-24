# End-to-End Test Flows for AwaazWeb

## Flow 1: Information Search & Preview
- Input: "Delhi se Bhopal ki kal ki train dhundho"
- Expected Plan: `{ "mode": "read", "goal": "Find trains from Delhi to Bhopal tomorrow", ... }`
- Expected Tool: TinyFish Search / Fetch
- Expected Output: 3 options with timings & prices in Hinglish.

## Flow 2: Follow-up Detail
- Input: "Doosri wali ki detail batao"
- Expected Output: Detailed breakdown of the second train.

## Flow 3: Risky Action Blocked by Safety Gate
- Input: "Yeh ticket book kar do"
- Expected Plan: `{ "mode": "act", "steps": [{ "description": "Book ticket", "risky": true }] }`
- Expected Status: `needs_confirmation`
- Spoken Confirmation Prompt: Exact action read back to user.
- Confirmation: "Haan" -> executes; "Nahi" -> cancels.

## Flow 4: User Intervention (OTP / Captcha)
- Input: Login / Checkout requiring OTP
- Expected Status: `needs_user_input`
- Action: Pauses and asks user to provide OTP safely without storing credentials.
