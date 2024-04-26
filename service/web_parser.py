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

        soup = BeautifulSoup(response['Message'], 'html.parser')
        blocks = soup.select('div[class=sortcompact]')

        for block in blocks:
            try:
                url = REGERING_URL + block.find('a')['href']
                title = block.find('a').text
                date_blocks = block.select('time')
                published = date_blocks[0]['datetime'] if date_blocks else None

                updated = None

                if len(date_blocks) > 1:
                    updated = date_blocks[1]['datetime']

                links = block.find_all('a', tabindex="-1")

                type_id, article_type = WebParser.extract_from_link(links[0])

                senders = []

                for link in links[1:]:
                    sender_id, sender = WebParser.extract_from_link(link)
                    senders.append({
                        'id': sender_id,
                        'name': sender
                    })

                document = {
                    'title': title,
                    'url': url,
                    'published': published,
                    'updated': updated,
                    'type': article_type,
                    'type_id': type_id,
                    'senders': senders
                }

                documents.append(document)
            except Exception as e:
                print(e)
                print(block)

        documents.reverse()
        return documents

    @staticmethod
    def extract_from_link(link):
        return link['href'].split('/')[-1], link.text
