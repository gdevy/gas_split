from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.post("/files/")
async def create_file(file: bytes = File(...)):
    return {"file_size": len(file)}


@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...)):
    print(Path(__file__) / file.filename)
    with open(Path(__file__).parent / file.filename, 'wb') as open_file:
        open_file.write(await file.read())

    return {"filename": file.filename}


@app.get("/uploadfile/", response_class=HTMLResponse)
async def read_items():
    html_content = """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
              <form action="http://localhost:8000/upload" method="post" enctype="multipart/form-data">
                  <p><input type="file" name="file">
                  <p><button type="submit">Submit</button>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
