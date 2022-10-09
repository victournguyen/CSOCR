"""
Title: Comic Strip Optical Character Recognition (CSOCR)
Authors: Victor Nguyen, Harry Liu

This program uses Dash and Materialize (CSS) to show a webpage where users can
upload one or more images that have text. The application will extract the text
from the images and display the images along with their extracted text in
addition to ordering them sequentially.

Dash is a Python library created by Plotly which uses React.js and Plotly.js to
make a Flask application. Materialize is a front-end framework developed by
Google, used here to make a simplistic website. Other libraries used include
base64, boto3, and gensim.

The inputted image files are encoded in Base64, so we decode these and then use
Amazon's Textract to read the text. As for ordering the various comic strip
segments, the segments are fed through Google's Word2Vec model and ordered by
the Word Mover's Distance. This works by comparing the word encodings of the
segments found in the pre-trained model. Overall, the HTML elements are
dynamically generated and ordered to be inserted into the application's layout.
"""
#-------------------------------Library Imports--------------------------------#
from dash import Dash, Input, Output, State, html, dcc
import base64
import boto3
import gensim.downloader as api
import json

#------------------------------API & Model Setup-------------------------------#
# Load AWS Secure Access Keys from JSON
with open('access.json') as file:
    access = json.load(file)
ACCESS_KEY_ID = access['ACCESS_KEY_ID']
SECRET_ACCESS_KEY = access['SECRET_ACCESS_KEY']
# Load Google's Word2Vec model
model = api.load('word2vec-google-news-300')
# Create the Textract client
textract = boto3.client(
    'textract',
    region_name='us-east-2',
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
)

#---------------------------------Application----------------------------------#
# Create Dash/Flask app with title
app = Dash(__name__)
title = 'Comic Strip Optical Character Recognition (CSOCR)'
app.title = title
# Server for deployment
application = app.server

# App layout
app.layout = html.Div(className='body', children=[
    html.Center(children=[
        # Title
        html.H3(id='title', children=title),
        # Multiple file upload
        dcc.Upload(id='upload', children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
        ]), multiple=True),
        # Output that will hold the image, its caption, and the extracted text
        html.Div(id='output')
    ])
])

#----------------------------------Functions-----------------------------------#
def gen_text(text):
    """
    This function splits the given text by line and puts each line into a
    paragraph element. This makes the extracted text match the visualization
    better due to the newline characters not being displayed in one paragraph.

    :param str text: The cleaned text prepared for display
    :return: List of paragraph elements each containing a line of text
    """
    # Separate the text into lines
    lines = text.split('\n')
    texts = []
    for i in range(len(lines)):
        # Apply class names for formatting the margins in order to keep the
        # paragraph elements together while still keeping the spacing before and
        # after the group.
        cn = ''
        if i < len(lines) - 1:
            cn += ' card-text-top'
        if i > 0:
            cn += ' card-text-bottom'
        texts.append(html.P(className=cn.strip(), children=lines[i]))
    return texts

def gen(content, name):
    """
    This function extracts the text from the image and builds the HTML elements
    to display the image along with its text. It returns a tuple with an HTML
    div and the text read by the model. The div is responsible for displaying
    the image, caption, and extracted text while the text is used to order the
    conversation.

    :param str content: Base64-encoded image string
    :param str name: File name of the image
    :return: Tuple of the HTML div and extracted text
    """
    # Decode the Base64 string
    img = base64.b64decode(content[content.find('base64,') + len('base64,'):])

    # Detect the text using the bytes of the image
    response = textract.detect_document_text(Document={'Bytes': img})

    # Read the text by line
    text = ''
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            # Preserve the newline
            text += item["Text"] + '\n'
    text = text.strip()

    # Display for a single image and extracted text
    return (html.Div(children=[
        html.Div(className='row', children=[
            html.Div(className='col s4 offset-s2', children=[
                # The image and its file name
                html.Figure(children=[
                    html.Img(src=content),
                    html.Figcaption(className='cap', children=name)
                ])
            ]),
            # Contains one paragraph element for each line
            html.Div(className='col s4 card-panel', children=gen_text(text))
        ])
    ]), text)

@app.callback(
    Output('output', 'children'),
    Input('upload', 'contents'),
    State('upload', 'filename')
)
def upload(contents, names):
    """
    This function is the callback function for the file upload, the connection
    from user input to the backend. It generates displays for each image and
    corresponding extracted text, orders these by the Word Mover's Distance, and
    returns them to the output container div.

    :param list contents: List of Base64-encoded images in the form of strings
    :param list names: List of file names for the images
    :return: List of divs for the images and their texts
    """
    if contents is not None:
        # Generate the HTML elements and text
        generated = [gen(c, n) for c, n in zip(contents, names)]
        # Select the first comic segment
        ordered = [generated[0]]
        generated.pop(0)
        # Iterate until all comic segments have been added to the ordered list
        while len(generated) > 0:
            min_dist = int(1e15)
            min_i = -1
            # Select the set of sentences that is closest to the most recently
            # added text, decided by the Word Mover's Distance
            for i in range(len(generated)):
                dist = model.wmdistance(
                    ordered[len(ordered) - 1][1].split(),
                    generated[i][1].split()
                )
                if dist < min_dist:
                    min_i = i
                    min_dist = dist
            ordered.append(generated[min_i])
            generated.pop(min_i)
        # Only return the HTML displays
        children = [item[0] for item in ordered]
        return children

#---------------------------------Program Run----------------------------------#
if __name__ == '__main__':
    # For running locally
    # app.run_server(port=8080, debug=True)
    # For deployment
    application.run(port=8080)