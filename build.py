import os
import requests
import markdown
from jinja2 import Environment, FileSystemLoader

ORG_NAME = "AccessMods"
GITHUB_TOKEN = os.environ.get('GH_TOKEN')
# Header to get pre-rendered HTML from GitHub (Reliable, no regex)
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.html" 
}
JSON_HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def get_dynamic_nav():
    nav_links = [{"title": "Home", "url": "index.html"}]
    if os.path.exists('content'):
        for filename in sorted(os.listdir('content')):
            if filename == 'index.md': continue 
            if filename.endswith('.md'):
                title = filename.replace('.md', '').replace('-', ' ').title()
                nav_links.append({"title": title, "url": filename.replace('.md', '.html')})
    return nav_links

def get_full_readme_html(repo_name):
    """
    Fetches the full, rendered HTML of the README.
    """
    try:
        url = f"https://api.github.com/repos/{ORG_NAME}/{repo_name}/readme"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.text
    except:
        pass
    return None

def get_org_data():
    try:
        url = f"https://api.github.com/orgs/{ORG_NAME}/repos?per_page=100"
        repos = requests.get(url, headers=JSON_HEADERS).json()
    except Exception as e:
        print(f"Error fetching repos: {e}")
        return ""
    
    cats = {"mod": "", "utility": "", "lib": ""}
    
    if isinstance(repos, list):
        repos.sort(key=lambda x: x['name'])

    for repo in repos:
        if not isinstance(repo, dict): continue
        if repo.get('archived') or repo.get('private'): continue
        
        topics = repo.get('topics', [])
        
        target = None
        if "game-mod" in topics: target = "mod"
        elif "utility" in topics: target = "utility"
        elif "library" in topics: target = "lib"
        
        if not target: continue

        # Releases
        buttons_html = ""
        version_tag = ""
        try:
            rel_url = f"https://api.github.com/repos/{ORG_NAME}/{repo['name']}/releases/latest"
            rel_resp = requests.get(rel_url, headers=JSON_HEADERS)
            
            if rel_resp.status_code == 200:
                data = rel_resp.json()
                version_tag = f"<span class='version-tag'>{data['tag_name']}</span>"
                for asset in data.get('assets', []):
                    if "source code" in asset['name'].lower(): continue
                    buttons_html += f'<a href="{asset["browser_download_url"]}" class="btn">{asset["name"]}</a> '
            else:
                version_tag = "<span class='version-tag'>Dev Build</span>"
                buttons_html = f'<a href="{repo["html_url"]}" class="btn secondary">View Source</a>'
        except:
            buttons_html = f'<a href="{repo["html_url"]}" class="btn secondary">View on GitHub</a>'

        # Get Full Readme
        readme_html = get_full_readme_html(repo['name'])
        
        # Build Description Block
        short_desc = repo['description'] or "No description provided."
        
        details_block = ""
        if readme_html:
            details_block = f"""
            <details>
                <summary>Read More</summary>
                <div class="readme-content">{readme_html}</div>
            </details>
            """

        card_html = f"""
        <div class="card">
            <div class="card-header">
                <h3><a href="{repo['html_url']}">{repo['name']}</a> {version_tag}</h3>
                <div class="btn-group">{buttons_html}</div>
            </div>
            <p><strong>{short_desc}</strong></p>
            {details_block}
        </div>
        """
        cats[target] += card_html

    return f"""
    <h2 id="mods">Game Mods</h2>
    {cats['mod'] or '<p>No mods found yet.</p>'}
    
    <h2 id="tools">User Utilities</h2>
    <p>Installers, patchers, and helper tools.</p>
    {cats['utility'] or '<p>No utilities found.</p>'}
    
    <h2 id="libs">Developer Resources</h2>
    <p>Libraries and code for mod creators.</p>
    {cats['lib'] or '<p>No libraries found.</p>'}
    """

def build():
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('base.html')
    nav_links = get_dynamic_nav()
    
    # Build Index
    repo_data = get_org_data()
    intro_html = ""
    if os.path.exists('content/index.md'):
        # utf-8-sig handles the Windows Notepad BOM issue
        with open('content/index.md', 'r', encoding="utf-8-sig") as f:
            intro_html = markdown.markdown(f.read())
            
    with open('index.html', 'w', encoding="utf-8") as f:
        f.write(template.render(title="Home", content=intro_html + repo_data, nav_links=nav_links))

    # Build Pages
    if os.path.exists('content'):
        for filename in os.listdir('content'):
            if filename == 'index.md': continue
            if filename.endswith('.md'):
                with open(f'content/{filename}', 'r', encoding="utf-8-sig") as f:
                    with open(filename.replace('.md', '.html'), 'w', encoding="utf-8") as w:
                        w.write(template.render(
                            title=filename.replace('.md','').title(), 
                            content=markdown.markdown(f.read()), 
                            nav_links=nav_links
                        ))

if __name__ == "__main__":
    build()