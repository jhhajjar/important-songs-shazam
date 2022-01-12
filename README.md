# Important Songs Shazam
Author: Joseph Hajjar

### Workflow
1. Scrapes the Shazam [Top 200](https://www.shazam.com/charts/top-200/united-states) to get the first `top_songs` number of songs (specified in `config.py`).
2. Chooses top 5 of those songs as important.
5. Calculates the ranking:shazams ratio for all the songs, and chooses the 5 songs with the best ratio.*
3. Gets the 10 Shazam [Discovery](https://www.shazam.com/charts/top-200/united-states) songs.
4. Loops through all of the cities' leaderboards and calculates where each song is doing the best.
4. Results written to excel.

*This is to capture the intuition that a song ranked #4 with 10k shazams is more "important" than a song ranked #2 100M shazams.

### Usage

Configurations can be made in the `config.py` file. To use the script, run `python3 main.py`. 

Dependencies:
* pandas
* selenium
* bs4
