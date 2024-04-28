import html
from bs4 import BeautifulSoup

REGERING_URL = 'https://www.regeringen.se'


class WebParser(object):

    @staticmethod
    def get_document_amount(response):
        htmlData = html.unescape(response.decode('utf-8'))
        soup = BeautifulSoup(htmlData, 'html.parser')

        amount = soup.select_one('strong[class==filterHitCount]')
        return int(amount.text)

    @staticmethod
    def get_document_list(response):
        documents = []

        if 'Message' not in response:
            return None, None

        soup = BeautifulSoup(response['Message'], 'html.parser')
        blocks = soup.select('div.sortcompact')
        codes = {}

        for block in blocks:
            try:
                url = REGERING_URL + block.find('a')['href']
                title = block.find('a').text
                dates = [t['datetime'] for t in block.select('time')]
                published = dates[0] if dates else None
                updated = dates[1] if len(dates) > 1 else None

                ps = block.select('p')
                is_sender = False
                types = []
                senders = []

                for content in ps[-1].contents:
                    if isinstance(content, str) and 'från' in content:
                        is_sender = True
                    elif content.name == 'a':
                        code, name = WebParser.extract_from_link(content)
                        codes[code] = name

                        if is_sender:
                            senders.append(code)
                        else:
                            types.append(code)

                document = {
                    'title': title,
                    'url': url,
                    'published': published,
                    'updated': updated,
                    'types': types,
                    'senders': senders,
                }

                if len(ps) > 1:
                    document['summary'] = ps[0].text.strip()

                documents.append(document)
            except Exception as e:
                print(e)
                print(soup)
                return None, None

        return documents, codes

    @staticmethod
    def extract_from_link(link):
        return int(link['href'].split('/')[-1]), link.text
