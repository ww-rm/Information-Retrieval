import json
from math import log
from pathlib import Path
from time import time_ns

import jieba
from tqdm import tqdm


def processdoc(doc):
    """将文档转换为tokens"""
    return jieba.cut(doc)


class IITable:
    """倒排索引表"""

    def __init__(self) -> None:
        self.docids = set()
        self.table = {}
        """
        {
            "word": {
                "freq": 1,
                "df": 1,
                "postings": {
                    "id": {"tf": 1},
                    "id": {"tf": 1},
                    ...
                }
            },
            ...
        }
        """

    def addterm(self, term: str, docid: str) -> None:
        """
        Args:
            term: 词项
            docid: 文档 id 字符串
        """
        docid = str(docid)
        self.docids.add(docid)
        if term in self.table:
            self.table[term]["freq"] += 1
            if docid in self.table[term]["postings"]:
                self.table[term]["postings"][docid]["tf"] += 1
            else:
                self.table[term]["postings"][docid] = {"tf": 1}
            self.table[term]["df"] = len(self.table[term]["postings"])
        else:
            self.table[term] = {
                "freq": 1,
                "df": 1,
                "postings": {docid: {"tf": 1}}
            }

    def gettfidf(self, docid: str, term: str) -> float:
        docid = str(docid)
        if term in self.table and docid in self.table[term]["postings"]:
            tf = self.table[term]["postings"][docid]["tf"]
        else:
            return 0
        df = self.table[term]["df"]
        N = len(self.docids)
        # 计算 TF*IDF值
        return tf*log(N/df)

    def get_terminfo(self, term) -> dict:
        """获取词项信息"""
        if term in self.table:
            return self.table[term]
        return {"freq": 0, "df": 0, "postings": {}}

    def get_posting(self, term) -> set:
        """获取某一个词项的倒排表记录"""
        if term in self.table:
            return set(self.table[term]["postings"].keys())
        return set()

    def save(self, savepath):
        with open(savepath, "w", encoding="utf8") as f:
            json.dump({"docids": list(self.docids), "table": self.table}, f, ensure_ascii=False)

    def load(self, savepath):
        with open(savepath, "r", encoding="utf8") as f:
            record = json.load(f)
        self.docids = set(record.get("docids"))
        self.table = record.get("table")


class MySearchEngine:
    def __init__(self) -> None:
        self.iitable = IITable()
        self.docpaths = {}

    def loadfiles(self, doc_dir):
        """加载文档集, 填充倒排索引表"""
        # self.docpaths.add(doc_dir)
        for docpath in tqdm(Path(doc_dir).iterdir(), "Documents"):
            self.docpaths[docpath.stem] = docpath.as_posix()

            doccontent = docpath.read_text("utf8", errors="ignore")
            tokens = processdoc(doccontent)
            for token in tokens:
                self.iitable.addterm(token, docpath.stem)

    def gettext(self, term: str, docid: str) -> list:
        """返回包含 term 的文档片段"""
        content = Path(self.docpaths[docid]).read_text(encoding="utf8", errors="ignore")
        if len(content) > 300:
            content = content[:300] + "..."
        return content

    def loadfilepaths(self, doc_dir):
        for docpath in tqdm(Path(doc_dir).iterdir(), "Documents"):
            self.docpaths[docpath.stem] = docpath.as_posix()

    def _parse_boolean_query(self, query: str) -> list:
        """将布尔查询解析成后缀表达式"""
        ops = {"not": 0, "and": 1, "or": 2}
        stack_op = []
        stack_word = []
        token = ""
        for c in query.strip():
            if c in {"(", ")", " "}:
                if token:
                    if token.lower() in ops:
                        token = token.lower()
                        while stack_op and (stack_op[-1] in ops) and ops[token] > ops[stack_op[-1]]:
                            stack_word.append(stack_op.pop())
                        stack_op.append(token)
                    else:
                        stack_word.append(token)
                    token = ""

                if c == "(":
                    stack_op.append(c)
                elif c == ")":
                    while stack_op:
                        op = stack_op.pop()
                        if op == "(":
                            break
                        stack_word.append(op)
                else:
                    continue
            else:
                token += c
        if token:
            stack_word.append(token)
            token = ""

        while stack_op:
            stack_word.append(stack_op.pop())

        return stack_word

    def _boolean_search(self, query: str) -> set:
        full_set = set(self.docpaths.keys())
        stack = []
        query = self._parse_boolean_query(query)
        print(query)
        for token in query:
            if token == "not":
                t1 = stack.pop()
                stack.append(full_set.difference(t1))
            elif token == "and":
                t1 = stack.pop()
                t2 = stack.pop()
                stack.append(t1.intersection(t2))
            elif token == "or":
                t1 = stack.pop()
                t2 = stack.pop()
                stack.append(t1.union(t2))
            else:
                stack.append(self.iitable.get_posting(token))

        return stack[0]

    def _simple_search(self, query: str):
        # query each keyword by order
        query = query.strip().split()
        result_set = set(self.docpaths.keys())
        result_status = (True, len(query))
        for word in query:
            _result_set = result_set.intersection(
                self.iitable.get_posting(word)
            )
            # 保留上一次非空结果集
            if _result_set:
                result_set = _result_set
            else:
                result_status = (False, query.index(word))
                if query.index(word) == 0:
                    result_set = set()
                break

        # calculate tfidf score
        tfidf_score = {}
        for docid in result_set:
            tfidf_score[docid] = sum(
                self.iitable.gettfidf(docid, word)
                for word in query[:result_status[1]]
            )
        result_set = sorted(result_set, key=lambda x: tfidf_score[x], reverse=True)
        return (result_set, result_status)

    def search_docs(self, mode, query) -> dict:
        """
        Args:
            mode: boolean, simple

        Returns:
            {
                "status": True,
                "result": [],
                "msg": "查询成功",
                "time": 0,
                "extra": {}
            }
        """
        print(query)
        if mode not in {"boolean", "simple"}:
            raise ValueError("无效的模式选项")

        result = {
            "status": True,
            "result": [],
            "msg": "查询成功",
            "time": 0,
            "extra": {}
        }
        start_time = time_ns()
        if mode == "boolean":
            try:
                doc_ids = self._boolean_search(query)
                end_time = time_ns()
            except:
                result["status"] = False
                result["msg"] = "查询语句出错"
            else:
                result["result"] = list(doc_ids)
                result["time"] = "{:.6f}".format((end_time-start_time)/1e9)
        elif mode == "simple":
            try:
                doc_ids, status = self._simple_search(query)
                end_time = time_ns()
            except:
                result["status"] = False
                result["msg"] = "查询语句出错"
            else:
                result["result"] = list(doc_ids)
                result["time"] = "{:.6f}".format((end_time-start_time)/1e9)
                result["extra"]["match_num"] = status[1]  # 匹配关键词的个数

        return result


if __name__ == "__main__":
    se = MySearchEngine()
    se.loadfiles("./data/news/"),
    se.iitable.save("./data/iitable.json.dat")
