import datetime
import os
import requests
from dateutil import relativedelta
from lxml import etree

# -- config --

HEADERS = {
    "Authorization": f"Bearer {os.environ['ACCESS_TOKEN']}",
    "Accept": "application/vnd.github+json",
}

USER_NAME = os.environ["USER_NAME"]
BIRTHDAY = datetime.datetime(2006, 2, 4)
SVG_FILE = "profile.svg"

# --


def uptime():
    diff = relativedelta.relativedelta(datetime.datetime.now(), BIRTHDAY)

    def plural(n, word):
        return f"{n} {word}{'s' if n != 1 else ''}"

    return "{}, {}, {}".format(
        plural(diff.years, "year"),
        plural(diff.months, "month"),
        plural(diff.days, "day"),
    )


def fetch(query, variaveis):
    r = requests.post(
        "https://api.github.com/graphql",
        json={
            "query": query,
            "variables": variaveis,
        },
        headers=HEADERS,
        timeout=30,
    )

    if r.status_code != 200:
        raise Exception(
            f"GitHub API error {r.status_code}: {r.text}"
        )

    data = r.json()

    # GraphQL pode retornar HTTP 200 e ainda conter erros
    if data.get("errors"):
        print("GitHub GraphQL retornou avisos/erros:")
        for error in data["errors"]:
            print(" -", error.get("message", error))

    return data


def get_status():
    ano = datetime.datetime.now(datetime.UTC).year

    inicio = f"{ano}-01-01T00:00:00Z"
    fim = f"{ano}-12-31T23:59:59Z"

    query = """
    query($login: String!, $start: DateTime!, $end: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $start, to: $end) {
                contributionCalendar {
                    totalContributions
                }
            }

            repositories(
                ownerAffiliations: OWNER
                first: 100
            ) {
                totalCount

                edges {
                    node {
                        name

                        stargazers {
                            totalCount
                        }
                    }
                }
            }
        }
    }
    """

    data = fetch(
        query,
        {
            "login": USER_NAME,
            "start": inicio,
            "end": fim,
        },
    )

    user = data.get("data", {}).get("user")

    if user is None:
        raise Exception(
            f'Usuário "{USER_NAME}" não encontrado ou inacessível pela API.'
        )

    commits = (
        user["contributionsCollection"]
        ["contributionCalendar"]
        ["totalContributions"]
    )

    repositories = user["repositories"]

    repos = repositories["totalCount"]

    stars = 0

    for edge in repositories.get("edges", []):
        node = edge.get("node")

        # Alguns repositórios podem aparecer como null
        # por permissões ou limitações da API.
        if node is None:
            print("[aviso] repositório inacessível ignorado")
            continue

        stargazers = node.get("stargazers")

        if stargazers:
            stars += stargazers.get("totalCount", 0)

    return commits, repos, stars


def update_svg(commits, repos, stars):
    tree = etree.parse(SVG_FILE)
    root = tree.getroot()

    fields = {
        "uptime_data": uptime(),
        "commit_data": f"{commits:,}",
        "repo_data": str(repos),
        "star_data": str(stars),
    }

    for element_id, value in fields.items():
        el = root.find(f".//*[@id='{element_id}']")

        if el is not None:
            el.text = value
            print(f"atualizado: {element_id} = {value}")
        else:
            print(f'[aviso] id "{element_id}" nao encontrado')

    tree.write(
        SVG_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print("profile.svg atualizado!")


if __name__ == "__main__":
    print("buscando dados...")

    commits, repos, stars = get_status()

    print(f"  commits: {commits}")
    print(f"  repos:   {repos}")
    print(f"  stars:   {stars}")
    print(f"  uptime:  {uptime()}")

    update_svg(commits, repos, stars)