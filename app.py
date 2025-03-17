from twilio.twiml.voice_response import VoiceResponse, Gather, Say
from twilio.rest import Client
from flask import Flask, request, url_for, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Replace these values with your actual Twilio credentials
account_sid = 'AC38b66ee5cbe4955ce6ff161f27fdf12c'
auth_token = '193b050aa895103f1c0911f6fe99443a'
client = Client(account_sid, auth_token)


@app.route("/ivr", methods=['POST'])
def ivr():
    response = VoiceResponse()

    # Step 1: Welcome message and gather mobile number
    gather = Gather(num_digits=10, action='/gather_mobile', method='POST', input='dtmf speech',
                    speech_model='phone_call', timeout=10)
    gather.say(
        "Thank you for calling HelpDesk. You have reached Pearl, our automated password reset system. To begin, please enter or say the 10-digit mobile number associated with your account.")
    response.append(gather)

    response.redirect('/ivr')
    return str(response)


@app.route("/gather_mobile", methods=['POST'])
def gather_mobile():
    response = VoiceResponse()
    mobile_number = request.form.get('Digits') or request.form.get('SpeechResult')

    # Logging received input for debugging
    print(f"Mobile Number Received: {mobile_number}")

    if mobile_number and len(mobile_number) == 10:
        # Convert mobile number to digit-by-digit format
        mobile_number_readable = " ".join([number_to_word(digit) for digit in mobile_number])

        gather = Gather(num_digits=1, action=f'/confirm_mobile?mobile={mobile_number}', method='POST',
                        input='dtmf speech', speech_model='phone_call', timeout=5)
        gather.say(
            f"You entered {mobile_number_readable}. If this is correct, press or say 1. To re-enter your mobile number, press or say 2.")
        response.append(gather)
    else:
        response.say(
            "I’m sorry, I didn’t recognize that number. Please try again by entering or saying the 10-digit mobile number associated with your account.")
        response.redirect('/ivr')

    return str(response)


@app.route("/confirm_mobile", methods=['POST'])
def confirm_mobile():
    response = VoiceResponse()
    digit = request.form.get('Digits') or request.form.get('SpeechResult')
    mobile_number = request.args.get('mobile')

    # Logging received input for debugging
    print(f"Confirmation Received: {digit}")

    if digit == '1':
        gather = Gather(num_digits=8, action=f'/gather_additional?mobile={mobile_number}', method='POST',
                        input='dtmf speech', speech_model='phone_call', timeout=10)
        gather.say("Please enter Date of Birth associated with your account for additional verification.")
        response.append(gather)
    elif digit == '2':
        response.redirect('/ivr')
    else:
        response.say("Invalid input. The call will now be disconnected.")
        response.hangup()

    return str(response)


@app.route("/gather_additional", methods=['POST'])
def gather_additional():
    response = VoiceResponse()
    additional_number = request.form.get('Digits') or request.form.get('SpeechResult')
    mobile_number = request.args.get('mobile')

    # Logging received input for debugging
    print(f"Additional Number Received: {additional_number}")

    if additional_number and len(additional_number) == 8:
        additional_number_readable = " ".join([number_to_word(digit) for digit in additional_number])

        gather = Gather(num_digits=1,
                        action=f'/confirm_additional?mobile={mobile_number}&additional={additional_number}',
                        method='POST', input='dtmf speech', speech_model='phone_call', timeout=5)
        gather.say(
            f"You entered {additional_number_readable}. If this is correct, press or say 1. To re-enter the number, press or say 2.")
        response.append(gather)
    else:
        response.say(
            "I’m sorry, I didn’t recognize that number. Please try again by entering or saying the 8-digit number.")
        response.redirect(f'/confirm_mobile?mobile={mobile_number}')

    return str(response)


@app.route("/confirm_additional", methods=['POST'])
def confirm_additional():
    response = VoiceResponse()
    digit = request.form.get('Digits') or request.form.get('SpeechResult')
    mobile_number = request.args.get('mobile')
    additional_number = request.args.get('additional')

    # Logging received input for debugging
    print(f"Final Confirmation Received: {digit}")
    print(f"Mobile Number: {mobile_number}, Additional Number: {additional_number}")

    if digit == '1':
        # Ensure the phone number is in E.164 format with +91 for Indian numbers
        if not mobile_number.startswith('+'):
            mobile_number = f"+91{mobile_number}"  # Add country code for India

        # Generate the link to the form
        url = url_for('user_form', mobile=mobile_number, additional=additional_number, _external=True)

        try:
            # Send the SMS
            client.messages.create(
                to=mobile_number,
                from_='+19896854436',  # Replace with your Twilio phone number
                body=f"Please fill out the form using the following link for password reset: {url}"
            )
            response.say(
                "Your information has been validated. Please check your text messages and follow the instructions to continue with the reset process. Thank you. Goodbye.")
        except Exception as e:
            print(f"Error sending SMS: {e}")
            response.say("There was an error sending the SMS. Please try again later.")

        response.hangup()
    elif digit == '2':
        response.redirect(f'/confirm_mobile?mobile={mobile_number}')
    else:
        response.say("Invalid input. The call will now be disconnected.")
        response.hangup()

    return str(response)


@app.route("/user_form", methods=['GET', 'POST'])
def user_form():
    mobile_number = request.args.get('mobile')
    additional_number = request.args.get('additional')

    file_path = f'C:\\Users\\SVC-RPA-DEV01\\Desktop\\VirtualAgent\\Requested\\{mobile_number}.xlsx'

    if request.method == 'POST':
        # Get form data from the POST request
        userid = request.form['userid']
        application_name = request.form['application_name']

        # Save the data to an Excel file with a blank 'Reset Password' field
        save_to_excel(userid, application_name, mobile_number, additional_number)

        # After submitting, display a message to wait for the password reset
        return f'''
           <div style="text-align:center; margin-top:50px;">
                <img src="{url_for('sgx_logo')}" alt="Solugenix Logo" style="width:150px; height:auto;">
                <h3>Password Reset Form</h3>
            </div>
            <p style="text-align:center;">Your information has been submitted. Please wait while we reset your password.</p>
            <p style="text-align:center;"><a href="{url_for('user_form', mobile=mobile_number ,additional=additional_number)}">Refresh to check password reset status</a></p>
        '''

    # Check if the Excel file exists and has the 'Reset Password' field filled
    reset_password = check_reset_password(file_path)

    if reset_password:
        return f'''
            <div style="text-align:center; margin-top:50px;">
                <img src="{url_for('sgx_logo')}" alt="Solugenix Logo" style="width:150px; height:auto;">
                <h3>Password Reset Form</h3>
            </div>
            <p style="text-align:center; color:green;">Password reset Successful: Here is your New Password: <b>{reset_password}</b></p>
            <p style="text-align:center; color:Blue;">Thank you for using Pearl, the Solugenix automated password reset system. Have a great day!</p>
        '''
    else:
        return f'''
           <div style="text-align:center; margin-top:50px;">
                <img src="{url_for('sgx_logo')}" alt="Solugenix Logo" style="width:150px; height:auto;">
                <h3>Password Reset Form</h3>
            </div>
            <form method="POST" style="width:300px; margin:auto; background-color:#f2f2f2; padding:20px; border-radius:10px; box-shadow: 0px 0px 15px rgba(0, 0, 0, 0.1);">
                <div style="margin-bottom:15px;">
                    <b style="color:#4B0082;"><label for="userid">UserID:</label></b><br>
                    <input type="text" name="userid" id="userid" required style="width:100%; padding:10px; border-radius:5px; border:1px solid #ccc;">
                </div>
                <div style="margin-bottom:15px;">
                    <b style="color:#4B0082;"><label for="application_name">Application Name:</label></b><br>
                    <select name="application_name" id="application_name" required style="width:100%; padding:10px; border-radius:5px; border:1px solid #ccc;">
                        <option value="Sonic">Inspire Partner Net</option>
                        <option value="Tot Zone">Tot Zone</option>
                        <option value="Solugenix">Sonic Partner Net</option>
                    </select>
                </div>
                <div style="text-align:center;">
                    <input type="submit" value="Submit" style="background-color:#007bff; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer;">
                </div>
            </form>
        '''
@app.route('/sgx_logo')
def sgx_logo():
    # Correct the file path to your image directory
    return send_from_directory('C:/Users/SVC-RPA-DEV01/Desktop', 'Sgx.jpg')


def save_to_excel(userid, application_name, mobile_number, additional_number):
    file_path = f'C:\\Users\\SVC-RPA-DEV01\\Desktop\\VirtualAgent\\Requested\\{mobile_number}.xlsx'
    df = pd.DataFrame({
        'UserID': [userid],
        'Application Name': [application_name],
        'Phone Number': [mobile_number],
        'Additional Number': [additional_number],
        'Reset Password': ['']
    })
    df.to_excel(file_path, index=False)


def check_reset_password(file_path):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        reset_password = df.get('Reset Password', [''])[0]
        if reset_password:
            return reset_password
    return None


def number_to_word(digit):
    words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    return words[digit]


if __name__ == "__main__":
    app.run(debug=True)
