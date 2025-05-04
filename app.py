from flask import Flask, render_template
import pandas as pd
import bs4 as bs
from urllib.request import Request, urlopen
import ssl

app = Flask(__name__)

@app.route("/")
def index():
    # Scrape data
    url = "https://www.dataroma.com/m/grid.php"
    context = ssl._create_unverified_context()
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36')
    rawpage = urlopen(req, context=context).read()
    soup = bs.BeautifulSoup(rawpage, 'html.parser')
    tbl = soup.find("table", {"id": "grid"})
    df = pd.read_html(str(tbl))[0]

    # Flatten and reformat
    rows = []
    for index, row in df.iterrows():
        for col in df.columns:
            rows.append((col, row[col]))
    df = pd.DataFrame(rows, columns=["Type", "Raw"])
    
    # Extract structured data
    df['Rank'] = range(len(df))
    df['Ticker'] = df['Raw'].apply(lambda x: x.split(" ", 1)[0].strip())
    df['Company Name'] = df['Raw'].apply(lambda x: x.split(" ", 1)[1].split("(", 1)[0].strip())
    df['Sector'] = df['Raw'].apply(lambda x: x.split("(", 1)[1].split(")", 1)[0].strip())
    df['Superinvestor Ownership'] = df['Raw'].apply(
        lambda x: x.split("Superinvestor Ownership : ", 1)[1].split(" ", 1)[0].strip()
        if "Superinvestor Ownership :" in x else "0"
    )
    df['Hold Price'] = df['Raw'].apply(
        lambda x: x.split("Hold Price:")[1].strip() if "Hold Price:" in x else "$0"
    )

    df = df.drop(['Type', 'Raw'], axis=1)

    # Render to template
    return render_template("index.html", table=df.to_html(classes="table table-striped", index=False, border=0, escape=False))

if __name__ == "__main__":
    app.run(debug=True)
