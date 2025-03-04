# g0vse

![Logo of the g0vse project](./g0vse.png)

g0vse is a project aiming to make the information available on the Swedish government's website ([regeringen.se](https://www.regeringen.se)) more accessible.

You can read more about the project on the website [g0v.se](https://g0v.se). The following documentation on Github focuses on the technical aspects of the project.

## What data is available?

g0vse uses the regeringen.se search API to fetch the vast majority of the website's pages. For each page, the following information is saved:

- title: the page title, which often contains the name of the report, bill, etc.
- url: the url of the page, which also contains information about the page's object ("/remisser/", "/proposition/")
- id: the subtitle of the page, which often contains the serial number of the object (*beteckningsnummer*)
- summary: the excerpt of the page describing its content
- published & updated: the date when the page was published or updated
- types: the types of the page's object as codes*
- senders: the senders (often ministers) as codes*
- categories: the page's categories as codes*
- shortcuts: links to related pages that can be found on the right side of the page
- attachments: links to documents, usually the most interesting part if you want to download public investigations (*sou, ds, pm*), public feedback letters (*remissvar*), etc.

*The codes are used on the website to categorize content and a [list of codes can be found here](https://g0v.se/api/codes.json).

### API routes

The logic behind the API routes is to follow the structure of the government's website as much as possible. For instance, a list of the bills is available at [regeringen.se/rapporter](https://regeringen.se/rapporter) and the corresponding API route is [g0v.se/rapporter.json](https://g0v.se/rapporter.json). A complete list of routes is available at [g0v.se](https://g0v.se).

The route [/api/latest_updated.json](https://g0v.se/api/latest_updated.json) can be used to know when the data was last updated.

In addition, the text of each page is available as Markdown. For example, [regeringen.se/artiklar/2024/10/sjukvardsminister-[...]-sjukvarden/](https://regeringen.se/artiklar/2024/10/sjukvardsminister-acko-ankarberg-johansson-om-budgetsatsningar-pa-halso--och-sjukvarden/) is available at [g0v.se/artiklar/2024/10/sjukvardsminister-[...]-sjukvarden.md](https://g0v.se/artiklar/2024/10/sjukvardsminister-acko-ankarberg-johansson-om-budgetsatsningar-pa-halso--och-sjukvarden.md).

If you are unsure of what is available, you can try the [URL converter](https://g0v.se) or browse the files on [Github](https://github.com/civictechsweden/g0vse/tree/data).

License for the data is unclear as Sweden doesn't have a modern law for access to public information where a default license could be specified and the government chancellery hasn't provided one either. In practice, it's safe to reuse.

### Data quality issues

The data was fetched through webscraping from a website used by thousands of civil servants from various departments, with their own methods and who never thought about the information being digitally reused by others.

As a result, the data quality is not necessarily that good. Here are a few examples of issues that you will need to address when reusing:

- the field *id* needs to be cleaned in order to extract an actual identifier for the document of the page
- the field title will also use different norms
- attachments are just provided with their name and a URL to fetch them. File names do not follow any convention, often contain typos and links are sometimes dead if the files have been removed.
- some pages are not marked as updated although they have new content (some remiss-pages, for instance, although far from the majority)
- departments have different methods when it comes to connecting their documents. Some use a component on the page called the "*lagstiftnings-/beslutkedjan*", others simply add the previous documents of the chain as a shortcut (in the *genvägar* box)
- the logic for parsing the *lagstiftningskedjor* is already written, but unfortunately, the lack of reliable page identifiers and consistency in the data makes it hard to use for now. It's coming though!

## How does g0vse work?

g0vse is composed of three components:

- a webscraper able to download a list of pages and the content of these pages
- a parser to convert the content in the HTML pages into Markdown and structured JSON objects
- a website to present the project and make it easier to understand what is available.

g0vse can be run by anyone on a local machine but the webscraper and parser are executed each night at 03:00 CET in order to fetch new content that was published the day before.

### The Webscraper

The webscraper's logic can be found mainly in [downloader.py](./services/downloader.py). It uses Selenium and a headless browser.

### The parser

The parser's logic can be found mainly in [web_parser.py](./services/web_parser.py). It uses the Python framework beautifulsoup4.

### The scheduled workflows

Each night at 03:00 CET, the code is executed through a [Github Action](https://github.com/civictechsweden/g0vse/blob/master/.github/workflows/download.yml), the data is updated on the branch [data](https://github.com/civictechsweden/g0vse/tree/data) and [deployed](https://github.com/civictechsweden/g0vse/blob/master/.github/workflows/static.yml) at [g0v.se](https://g0v.se).

### The frontend

To present the project, a lightweight static website has been built using NextJS and TailwindCSS. Its code is in the [frontend](./frontend/) folder.

## What if I want to reuse the code?

Go ahead! You'll need Python 3 and to install dependencies using:

```bash
pip install -r requirements.txt
```

After that, you can fetch the latext 20 items and associated codes:

```python
from services.downloader import Downloader

items, codes = downloader.get_latest_items(20)
```

You can also download a page and parse its content using:

```python
from services.downloader import Downloader
from services.web_parser import extract_page

page = downloader.get_webpage(url)
md_content, metadata = extract_page(page)
```

Have a look at [fetch.py](./fetch.py) for more complex logic that can download all articles or just the missing ones.

## Updating the data manually

As written above, the data is downloaded regularly and stored on the [data](https://github.com/civictechsweden/g0vse/tree/data) branch of this Github repository.

If you want to fetch this data from Github and update it using the [fetch.py](./fetch.py) script, it is recommended to proceed this way:

- Clone the data from the *data* branch in a folder called *data*:
```bash
git clone --branch data --single-branch https://github.com/civictechsweden/g0vse.git data
```
- Run the script (it will read the data and only download the new pages):
```bash
python fetch.py
```

If you want to push the new data to the branch:
```bash
cd data
git add .
git -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit -m "Update data"
git push
```

## License

The code is licensed under AGPLv3.
