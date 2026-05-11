import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Death Discography Dashboard",
    layout="wide"
)

DATA_PATH = "death_tracks_final.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)

    if "bpm_final" in df.columns:
        df["bpm"] = df["bpm_final"]

    df["release_date"] = pd.to_datetime(
    df["release_date"],
    format="mixed",
    errors="coerce"
)
    df["release_year"] = df["release_date"].dt.year
    df["duration_min"] = df["duration_ms"] / 60000

    numeric_cols = [
        "bpm",
        "duration_min",
        "lastfm_track_listeners",
        "lastfm_track_playcount"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

df = load_data()

album_order = (
    df[["album_name", "release_date"]]
    .drop_duplicates()
    .sort_values("release_date")["album_name"]
    .tolist()
)

st.title("Death Discography Dashboard")
st.caption("A data-driven look at Death’s official studio albums, track performance, BPM, duration, and fan engagement.")

# Sidebar
selected_albums = st.sidebar.multiselect(
    "Select albums",
    album_order,
    default=album_order
)

filtered_df = df[df["album_name"].isin(selected_albums)]

# KPIs
total_albums = filtered_df["album_name"].nunique()
total_tracks = len(filtered_df)
avg_bpm = filtered_df["bpm"].mean()
total_listeners = filtered_df["lastfm_track_listeners"].sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Studio albums", total_albums)
col2.metric("Official tracks", total_tracks)
col3.metric("Average BPM", round(avg_bpm, 1))
col4.metric("Total track listeners", f"{int(total_listeners):,}")

st.divider()

# Album artwork grid
st.subheader("Studio Albums")

album_info = (
    filtered_df[["album_name", "release_date", "artwork_url"]]
    .drop_duplicates()
    .sort_values("release_date")
)

cols = st.columns(4)

for i, row in enumerate(album_info.itertuples()):
    with cols[i % 4]:
        st.image(row.artwork_url, use_container_width=True)
        st.markdown(f"**{row.album_name}**")
        st.caption(row.release_date.year)

st.divider()

# Album-level summary
st.subheader("Album Overview")

album_summary = (
    filtered_df
    .groupby("album_name", as_index=False)
    .agg(
        release_date=("release_date", "min"),
        tracks=("official_track_name", "count"),
        avg_bpm=("bpm", "mean"),
        avg_duration=("duration_min", "mean"),
        total_listeners=("lastfm_track_listeners", "sum"),
        total_playcount=("lastfm_track_playcount", "sum")
    )
    .sort_values("release_date")
)

fig_album_listeners = px.bar(
    album_summary,
    x="album_name",
    y="total_listeners",
    title="Total Last.fm Listeners by Album",
    labels={
        "album_name": "Album",
        "total_listeners": "Total listeners"
    }
)

st.plotly_chart(fig_album_listeners, use_container_width=True)

fig_bpm_evolution = px.line(
    album_summary,
    x="release_date",
    y="avg_bpm",
    markers=True,
    text="album_name",
    title="Average BPM Evolution Across Albums",
    labels={
        "release_date": "Release date",
        "avg_bpm": "Average BPM"
    }
)

st.plotly_chart(fig_bpm_evolution, use_container_width=True)

st.divider()

# Track analytics
st.subheader("Track Analytics")

left, right = st.columns(2)

with left:
    top_tracks = filtered_df.sort_values(
        "lastfm_track_listeners",
        ascending=False
    ).head(10)

    fig_top_tracks = px.bar(
        top_tracks,
        x="lastfm_track_listeners",
        y="official_track_name",
        color="album_name",
        orientation="h",
        title="Top 10 Tracks by Last.fm Listeners",
        labels={
            "official_track_name": "Track",
            "lastfm_track_listeners": "Listeners",
            "album_name": "Album"
        }
    )

    fig_top_tracks.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_top_tracks, use_container_width=True)

with right:
    fig_bpm_dist = px.histogram(
        filtered_df.dropna(subset=["bpm"]),
        x="bpm",
        nbins=20,
        title="BPM Distribution",
        labels={"bpm": "BPM"}
    )

    st.plotly_chart(fig_bpm_dist, use_container_width=True)

st.divider()

# Fastest / slowest / longest / shortest
st.subheader("Extremes")

fastest = filtered_df.dropna(subset=["bpm"]).sort_values("bpm", ascending=False).iloc[0]
slowest = filtered_df.dropna(subset=["bpm"]).sort_values("bpm", ascending=True).iloc[0]
longest = filtered_df.sort_values("duration_min", ascending=False).iloc[0]
shortest = filtered_df.sort_values("duration_min", ascending=True).iloc[0]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Fastest song", fastest["official_track_name"], f'{round(fastest["bpm"], 1)} BPM')
c2.metric("Slowest song", slowest["official_track_name"], f'{round(slowest["bpm"], 1)} BPM')
c3.metric("Longest song", longest["official_track_name"], f'{round(longest["duration_min"], 2)} min')
c4.metric("Shortest song", shortest["official_track_name"], f'{round(shortest["duration_min"], 2)} min')

st.divider()

# Track table
st.subheader("Track Explorer")

display_cols = [
    "album_name",
    "official_track_number",
    "official_track_name",
    "release_date",
    "duration_min",
    "bpm",
    "lastfm_track_listeners",
    "lastfm_track_playcount"
]

st.dataframe(
    filtered_df[display_cols].sort_values(
        ["release_date", "official_track_number"]
    ),
    use_container_width=True
)

## Album vs Album

st.divider()

st.subheader("Album vs Album Comparison")

compare_col1, compare_col2 = st.columns(2)

with compare_col1:
    album_a = st.selectbox(
        "Select first album",
        album_order,
        index=0
    )

with compare_col2:
    album_b = st.selectbox(
        "Select second album",
        album_order,
        index=1
    )


def get_album_comparison_stats(df, album_name):
    album_df = df[df["album_name"] == album_name].copy()

    total_tracks = album_df["official_track_name"].nunique()
    total_listeners = album_df["lastfm_track_listeners"].sum()
    total_length = album_df["duration_min"].sum()

    fastest_song = album_df.dropna(subset=["bpm"]).sort_values(
        "bpm", ascending=False
    ).iloc[0]

    slowest_song = album_df.dropna(subset=["bpm"]).sort_values(
        "bpm", ascending=True
    ).iloc[0]

    most_listened = album_df.sort_values(
        "lastfm_track_listeners", ascending=False
    ).iloc[0]

    least_listened = album_df.sort_values(
        "lastfm_track_listeners", ascending=True
    ).iloc[0]

    return {
        "album_name": album_name,
        "release_date": album_df["release_date"].min(),
        "artwork_url": album_df["artwork_url"].iloc[0],
        "total_tracks": total_tracks,
        "total_listeners": total_listeners,
        "total_length": total_length,
        "fastest_song": fastest_song["official_track_name"],
        "fastest_bpm": fastest_song["bpm"],
        "slowest_song": slowest_song["official_track_name"],
        "slowest_bpm": slowest_song["bpm"],
        "most_listened_song": most_listened["official_track_name"],
        "most_listened_count": most_listened["lastfm_track_listeners"],
        "least_listened_song": least_listened["official_track_name"],
        "least_listened_count": least_listened["lastfm_track_listeners"]
    }


album_a_stats = get_album_comparison_stats(df, album_a)
album_b_stats = get_album_comparison_stats(df, album_b)

card1, card2 = st.columns(2)

def display_album_card(stats):
    st.image(stats["artwork_url"], use_container_width=True)

    st.markdown(f"### {stats['album_name']}")
    st.caption(f"Released: {stats['release_date'].strftime('%d %B %Y')}")

    st.metric("Total listeners", f"{int(stats['total_listeners']):,}")
    st.metric("Total tracks", stats["total_tracks"])
    st.metric("Total length", f"{round(stats['total_length'], 2)} min")

    st.markdown("#### Song Highlights")

    st.write(f"**Fastest song:** {stats['fastest_song']} — {round(stats['fastest_bpm'], 1)} BPM")
    st.write(f"**Slowest song:** {stats['slowest_song']} — {round(stats['slowest_bpm'], 1)} BPM")

    st.write(
        f"**Most listened song:** {stats['most_listened_song']} — "
        f"{int(stats['most_listened_count']):,} listeners"
    )

    st.write(
        f"**Least listened song:** {stats['least_listened_song']} — "
        f"{int(stats['least_listened_count']):,} listeners"
    )


with card1:
    display_album_card(album_a_stats)

with card2:
    display_album_card(album_b_stats)