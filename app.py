from math import ceil
from flask import Flask, render_template
from flask.globals import request
from werkzeug.utils import redirect

from se import MySearchEngine

app = Flask(__name__)
myse = MySearchEngine()


@app.route("/")
def index():
    return render_template("index.html", page_data={"qm": "kw"})


@app.route("/search")
def search():
    print(request.args)

    if request.args.get("qs"):
        query = request.args.get("qs")
        page_num = int(request.args.get("p") or 1)

        if request.args.get("qm") == "bl":
            search_result = myse.search_docs("boolean", query)
        else:
            search_result = myse.search_docs("simple", query)

        # 调整 page_num 到合理的范围, 一面显示十条
        page_num = min(max(1, int(page_num)), ceil(len(search_result["result"])/10))

        page_data = {
            "query": query,
            "p": page_num,
            "qm": request.args.get("qm"),
            "prev_page_num": max(1, page_num-1),
            "next_page_num": page_num+1,
            "total_num": len(search_result["result"])
        }

        # 返回某一面的结果
        docids = search_result["result"][(page_num-1)*10:(page_num-1)*10+10]

        # 获取文档内容
        content = []
        for docid in docids:
            content.append(myse.gettext("", docid))
        search_result["result"] = list(zip(docids, content))

        return render_template(
            "index.html",
            data=search_result,
            page_data=page_data
        )
    else:
        return redirect("/")


if __name__ == "__main__":
    print("应用启动中")
    myse.iitable.load("./data/iitable.json.dat")
    myse.loadfilepaths("./data/news/")
    app.run(host="127.0.0.1", port=80)
