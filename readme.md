# Information Retrieval

An IR homework, implemented a small search engine in a web app.

---

## Environment

Whole project was passed test on Windows 10 with python3.7.

Use `pip install -r requirements.txt` to install necessary packages.

## Dataset

Put pure plain txt files in a folder, the dir tree may like following.

```plain
data/
    news/
        1.txt
        2.txt
        ...
```

## Usage

If first time to run, use `python se.py` to build inverted index table, see details in file `se.py`.

Otherwise, use `python app.py` to start flask app and then visit <http://127.0.0.1:80> in your browser.

---

*If you think this project is helpful to you, plz star it and let more people see it. :)*