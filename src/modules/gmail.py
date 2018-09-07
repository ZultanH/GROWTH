import smtplib

def send_email(user, password, recipient, subject, body):
    gmail_user = user
    gmail_pwd = password
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_user, gmail_pwd)
    server.sendmail(FROM, TO, message)
    server.close()

def send_product_token(recipient, token):
    username = ""
    password = ""

    send_email(username, password, recipient, "GROWTH Product Token", f"--PRODUCT TOKEN FOR GROWTH SERVICES--\n Token: {token}" )
