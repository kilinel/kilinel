import datetime
import os
import requests
from dateutil import relativedelta
from lxml import etree

# -- config

HEADERS = {'authorization':'token' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME']
BIRTHDAY = datetime.datetime(2006,6,1)
SVG_FILE = 'profile.svg'

#-


def uptime():
    diff = relativedelta.relativedelta(datetime.datetime.today(), BIRTHDAY)
    def plural(n, word):
        return f"{n} {word}{'s' if n != 1 else ''}"
    return '{}, {}, {}'.format(
        plural(diff.years, 'year'),
        plural(diff.months, 'month'),
        plural(diff.days, 'day'),
    )


def fetch(query, variaveis):

    r = requests.post(
        'https://api.github.com/graphsql',
        json={'query': query, 'variables': variaveis},
        headers=HEADERS,
    )
    if r.status_code == 200:
        return r.json()
    raise Exception(f'GitHub API error {r.status_code} : {r.text}')

def get_status():
    ano = datetime.datetime.utcnow().year
    inicio = f'{ano}-01-01T00:00:00Z'
    fim = f'{ano}-12-31T23:59:59Z'

    query = '''
    query($login: String!, $start:DateTime!, $end:DateTime!) {
        user(login: $login){
            contributionsCollection(from: $start, to: $end) {
                contributionCalendar {totalContributions}
            }
            repositories(ownerAffiliations: OWNER, first: 100){
            totalCount
            edges{
            node {stargazers { totalCount } }
            }
            
            }
        }
    
    }'''
    data = fetch(query, {'login': USER_NAME,'start': inicio, 'end': fim})
    user = data['data']['user']

    commits = user['contributionsCollection']['contributionCalendar']['totalContributions']
    repos = user['repositories']['totalCount']
    stars = sum(e['node']['stargazers']['totalCount'] for e in user['repositories']['edges'])

    return commits,repos,stars



def update_svg(commits,repos,stars):

    tree = etree.parse(SVG_FILE)
    root = tree.getroot()

    fields = {
        'uptime_data': uptime(),
        'commit_data': f'{commits:,}',
        'repo_data': str(repos),
        'star_data': str(stars),
    }

    for element_id, value in fields.items():
        el = root.find(f".//*[@id='{element_id}]")
        if el is not None:
            el.text = value
        else:
            print(f'[aviso] id "{element_id}" não encontrado no SVG')

    tree.write(SVG_FILE, encoding='utf-8', xml_declaration=True)
    print('profile.svg atualizado!')


if __name__ == '__main__':
    print('buscando dados...')
    commits, repos, stars = get_status()
    print(f'  commits: {commits}')
    print(f'  repos:   {repos}')
    print(f'  stars:   {stars}')
    print(f'  uptime:  {uptime()}')
    update_svg(commits, repos, stars)
