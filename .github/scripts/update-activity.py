"""Refresh the profile's activity section from GitHub's public Events API pages."""

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


START = "<!-- activity:start -->"
END = "<!-- activity:end -->"
PROFILE_TZ = timezone(timedelta(hours=8))
WINDOW_DAYS = 28
PROJECT_NAMES = {
    "xiaodaigua-ray/ray-template": "Ray Template",
    "filemintapp/filemint": "FileMint",
    "filemintapp/homebrew-tap": "FileMint Homebrew Tap",
    "inhiblabcore/vue-hooks-plus": "VueHooks Plus",
}
TRAIL_STYLE = """  <style>
    :root { color-scheme: light dark; }
    .panel { fill: #faf7f2; stroke: #ded3c3; }
    .guides { stroke: #ddd0c0; }
    .fill { stop-color: #c98a55; }
    .trail { stroke: #a17049; }
    .inactive { fill: #978270; }
    .active { fill: #914919; }
    .label { fill: #635349; }

    @media (prefers-color-scheme: dark) {
      .panel { fill: #232120; stroke: #4d4138; }
      .guides { stroke: #514136; }
      .fill { stop-color: #d08a52; }
      .trail { stroke: #d29a6d; }
      .inactive { fill: #917a66; }
      .active { fill: #ffbb76; }
      .label { fill: #ccbeb0; }
    }
  </style>"""


def describe(event, repo):
    """Return a key for the short list and Markdown referencing the activity."""
    url = f"https://github.com/{repo}"
    label = PROJECT_NAMES.get(repo.lower(), repo.split("/")[1])
    kind = event["type"]
    payload = event["payload"]
    action = payload.get("action")

    if kind == "PushEvent" and payload.get("ref", "").startswith("refs/heads/"):
        return ("push", repo.lower()), f"[{label}]({url}/commits) 推送了更新"

    if kind == "PullRequestEvent":
        number = payload.get("number")
        merged = action == "merged" or (
            action == "closed" and (payload.get("pull_request") or {}).get("merged") is True
        )
        if type(number) is int and number > 0 and (action == "opened" or merged):
            state = "已合并" if merged else "已提交"
            return ("pr", repo.lower(), number), f"[{label} #{number}]({url}/pull/{number}) {state}"

    if kind == "ReleaseEvent" and action == "published":
        tag = (payload.get("release") or {}).get("tag_name") or ""
        if re.fullmatch(r"[0-9A-Za-z_.-]{1,60}", tag):
            return ("release", repo.lower(), tag), f"[{label} {tag}]({url}/releases/tag/{tag}) 已发布"
        return ("release", repo.lower()), f"[{label}]({url}/releases) 发布了新版本"

    return None


def collect(pages, owner, start, today):
    profile = f"{owner}/{owner}".lower()
    events = sorted(
        (event for page in pages for event in page),
        key=lambda event: event["created_at"],
        reverse=True,
    )
    counts = Counter()
    notes = {}
    for event in events:
        repo = event["repo"]["name"]
        if (
            event.get("public") is not True
            or repo.lower() == profile
            or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo)
        ):
            continue
        created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        day = created_at.astimezone(PROFILE_TZ).date()
        if not start <= day <= today:
            continue
        activity = describe(event, repo)
        if activity is None:
            continue
        counts[day] += 1
        key, description = activity
        notes.setdefault(key, f"- `{day:%m.%d}` {description}")

    latest = list(notes.items())[:4]
    # Reserve a slot for the latest release so it stays visible during busy weeks.
    if len(latest) == 4 and all(key[0] != "release" for key, _ in latest):
        release = next((note for note in notes.items() if note[0][0] == "release"), None)
        if release is not None:
            latest[-1] = release
    return counts, [note for _, note in latest]


def render_trail(counts, start, today):
    values = [counts[start + timedelta(days=i)] for i in range(WINDOW_DAYS)]
    peak_index = max(range(WINDOW_DAYS), key=lambda i: (values[i], i))
    peak = values[peak_index]
    scale = max(1, peak)
    points = [
        (40 + 880 * i / (WINDOW_DAYS - 1), 118 - 62 * (count / scale) ** 0.5, count)
        for i, count in enumerate(values)
    ]
    coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
    dots = "\n".join(
        f'  <circle class="{"active" if count else "inactive"}"'
        f' cx="{x:.1f}" cy="{y:.1f}" r="{4.3 if count else 2.5}"/>'
        for x, y, count in points
    )
    peak_star = ""
    if peak:
        x, y, _ = points[peak_index]
        peak_star = f'''
  <g class="active" transform="translate({x:.1f} {y:.1f})">
    <circle r="12" opacity=".16"/>
    <path d="M0 -8 Q1 -1 8 0 Q1 1 0 8 Q-1 1 -8 0 Q-1 -1 0 -8 Z"/>
  </g>'''
    total = sum(values)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="172" viewBox="0 0 960 172" role="img" aria-labelledby="title desc">
  <title id="title">Public activity from {start:%Y-%m-%d} to {today:%Y-%m-%d}</title>
  <desc id="desc">{total} events in {WINDOW_DAYS} days. One point per day, higher points indicate more events.</desc>
{TRAIL_STYLE}
  <defs>
    <linearGradient id="trail" x1="0" y1="0" x2="0" y2="1">
      <stop class="fill" stop-opacity=".26"/>
      <stop class="fill" offset="1" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect class="panel" x=".5" y=".5" width="959" height="171" rx="16"/>
  <path class="guides" d="M40 118H920M40 87H920M40 56H920" fill="none" stroke-dasharray="2 6"/>
  <polygon points="40,118 {coordinates} 920,118" fill="url(#trail)"/>
  <polyline class="trail" points="{coordinates}" fill="none" stroke-width="1.6" stroke-linejoin="round"/>
{dots}{peak_star}
  <g class="label" font-family="ui-monospace, Menlo, Consolas, monospace" font-size="18">
    <text class="active" x="40" y="36">{total} {"EVENT" if total == 1 else "EVENTS"}</text>
    <text x="40" y="150">{start:%m.%d}</text>
    <text x="920" y="150" text-anchor="end">{today:%m.%d}</text>
  </g>
</svg>
'''


def update_profile(pages, owner, today):
    readme_path = Path("README.md")
    readme = readme_path.read_text(encoding="utf-8")
    before, start_marker, rest = readme.partition(START)
    _, end_marker, after = rest.partition(END)
    if not start_marker or not end_marker or readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain one ordered pair of activity markers")

    start = today - timedelta(days=WINDOW_DAYS - 1)
    counts, notes = collect(pages, owner, start, today)
    section = "\n".join(notes) or "近期暂无可展示的公开开发活动。"
    trail = render_trail(counts, start, today)
    readme_path.write_text(f"{before}{START}\n{section}\n{END}{after}", encoding="utf-8")
    Path("assets/activity.svg").write_text(trail, encoding="utf-8")


if __name__ == "__main__":
    update_profile(json.load(sys.stdin), sys.argv[1], datetime.now(PROFILE_TZ).date())
