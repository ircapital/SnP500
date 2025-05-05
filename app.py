from flask import Flask, render_template
import pandas as pd
import bs4 as bs
from urllib.request import Request, urlopen
import ssl
import json
import ssl
import re
import requests

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
    df['Ticker'] = df['Raw'].apply(lambda x: x.split(" ", 1)[0].replace(".","-").strip())
    df['Company Name'] = df['Raw'].apply(lambda x: x.split(" ", 1)[1].split("(", 1)[0].strip())
    df['Sector'] = df['Raw'].apply(lambda x: x.split("(", 1)[1].split(")", 1)[0].strip())
    df['Superinvestor Ownership'] = df['Raw'].apply(
        lambda x: x.split("Superinvestor Ownership : ", 1)[1].split(" ", 1)[0].strip()
        if "Superinvestor Ownership :" in x else "0"
    )
    df['Hold Price($)'] = df['Raw'].apply(
        lambda x: x.split("Hold Price:")[1].strip() if "Hold Price:" in x else "$0"
    )

    df = df.drop(['Type', 'Raw'], axis=1)

    df = df[df['Rank'] < 300]

    # Add Yahoo Finance data
    df['Current Price($)'] = None
    df['Gains & Losses(%)'] = None
    df['52 Week Range'] = None
    df['52 Week Low(%)'] = None
    df['52 Week High(%)'] = None

    for index, row in df.iterrows():
        ticker = row['Ticker']
        try:
            url = f"https://finance.yahoo.com/quote/{ticker}"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            
            response = requests.get(url, headers=headers)
            soup = bs.BeautifulSoup(response.text, "html.parser")

            #####

            tbl =soup.find("div",{"data-testid":"quote-statistics"})

            fifty_two_week_range = tbl.find("fin-streamer", {"data-field": "fiftyTwoWeekRange"})

            if fifty_two_week_range:
                df.at[index, '52 Week Range'] = fifty_two_week_range.text.strip()
            else:
                df.at[index, '52 Week Range'] = None
            
            #####

            tbl =str(soup.find("span",{"data-testid":"qsp-price"}))

            current_price = tbl.split(">",1)[1].replace(" </span>","").strip()

            if current_price:
                df.at[index, 'Current Price($)'] = current_price.strip()
            else:
                df.at[index, 'Current Price($)'] = None

            df.at[index, '52 Week Low(%)'] = round((((float(current_price.replace(",","").strip()) / float(fifty_two_week_range.text.split("-")[0].replace(",","").strip()))-1)*100),2)

            df.at[index, '52 Week High(%)'] = round((((float(current_price.replace(",","").strip()) / float(fifty_two_week_range.text.split("-")[1].replace(",","").strip()))-1)*100),2)

        except Exception as e:
            df.at[index, 'Current Price($)'] = None
            df.at[index, 'Gains & Losses(%)'] = None
            df.at[index, '52 Week Range'] = None
            df.at[index, '52 Week Low(%)'] = None
            df.at[index, '52 Week High(%)'] = None
            
    df['Current Price($)'] = df['Current Price($)'].astype(float)
    df['Hold Price($)'] = df['Hold Price($)'].str.replace(",", "", regex=False)
    df['Hold Price($)'] = df['Hold Price($)'].str.replace("$", "", regex=False).astype(float)

    df['Gains & Losses(%)'] = round(((df['Current Price($)'] / df['Hold Price($)'])-1)*100,2)

    # Render to template
    return render_template("index.html", table=df.to_html(classes="table table-striped", index=False, border=0, escape=False))

if __name__ == "__main__":
    app.run(debug=True)
