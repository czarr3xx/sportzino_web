import requests
from bs4 import BeautifulSoup

proxies = {
  "https": "https://scraperapi.retry_404=true.device_type=desktop.max_cost=0:3efb70e21229203c57b903ab3f4527b3@proxy-server.scraperapi.com:8001"
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

response = requests.get("https://sportzino.com", proxies=proxies, headers=headers, verify=False)

soup = BeautifulSoup(response.text, 'html.parser')

# Try to locate game rows/cards
games = soup.select('.match-card, .betting-row, .game')  # Adjust class names after inspecting site

for game in games:
    title = game.select_one('.league, .title') or "No title"
    teams = game.select('.team-name, .participant')
    odds = game.select('.odds, .odd')

    print({
        'title': title.text.strip() if title else 'N/A',
        'team1': teams[0].text.strip() if len(teams) > 0 else 'N/A',
        'team2': teams[1].text.strip() if len(teams) > 1 else 'N/A',
        'odds': [o.text.strip() for o in odds]
    })
