import dialogflow
from google.api_core.exceptions import InvalidArgument
import os


def create_session(project_id, session_id):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    return session_client, session


def process_usertext(session_client, session, usertext, language_code):
    text_input = dialogflow.types.TextInput(text=usertext, language_code=language_code)
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
    except InvalidArgument:
        raise
    return response.query_result.intent.display_name, response.query_result.parameters.fields, response.query_result.fulfillment_text

def read_dialogflow():
    dia_information = []
    with open('dialogflow.txt') as file:
        for line in file:
            dia_information.append(line.strip('\n').split('=')[1])
        file.close()
    DIALOGFLOW_PROJECT_ID = dia_information[0]
    DIALOGFLOW_LANGUAGE_CODE = dia_information[1]
    GOOGLE_APPLICATION_CREDENTIALS = dia_information[2]
    return DIALOGFLOW_PROJECT_ID, DIALOGFLOW_LANGUAGE_CODE, GOOGLE_APPLICATION_CREDENTIALS

def main():
    DIALOGFLOW_PROJECT_ID, DIALOGFLOW_LANGUAGE_CODE, GOOGLE_APPLICATION_CREDENTIALS = read_dialogflow()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
    SESSION_ID = 'test2'
    session_client, session = create_session(project_id=DIALOGFLOW_PROJECT_ID, session_id=SESSION_ID)
    usertext = "Add Rap God to my playlist"
    intent, parameter, response = process_usertext(session_client=session_client, language_code=DIALOGFLOW_LANGUAGE_CODE, session=session, usertext=usertext)
    print(intent, '\n', parameter)

if __name__ == '__main__':
    main()

