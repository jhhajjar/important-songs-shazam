import pandas as pd
import numpy as np
import time
from selenium.webdriver.chrome.options import Options
from datetime import datetime as dt
from selenium import webdriver
from config import *
from bs4 import BeautifulSoup


def send_report(movers, top, discovered, cities):
    
    from_shz = pd.concat((top, discovered)).reset_index(drop=True).drop('movement', axis=1)
    movers = movers.drop('movement', axis=1)
    
    timestamp = str(dt.now()).replace(' ', 'T').replace('-','').replace(':','').split('.')[0]
    writer = pd.ExcelWriter(f'report-{timestamp}.xlsx', engine='xlsxwriter')

    from_shz.to_excel(writer, sheet_name='Most popular and Discovered', index=False)
    movers.to_excel(writer, sheet_name='Best rank-shazams ratio', index=False)
    cities.to_excel(writer, sheet_name='Best cities for songs', index=False)

    writer.save()


def get_soup(browser: webdriver.Chrome, link: str):
    browser.get(link)
    time.sleep(1)

    # now that we have slept for 2 seconds the page should be properly loaded
    temp_soup = BeautifulSoup(browser.page_source, 'html.parser')
    soup = BeautifulSoup(temp_soup.prettify(), 'html.parser')

    return soup

# loops through all songs and cities to find where each song ranks in each city
def get_song_rank_by_city(browser: webdriver.Chrome, cities: list, df: pd.DataFrame):
    matrix = np.zeros((df.shape[0], len(cities))) + 51

    # matrix is (songs, cities) where matrix(i, j) is song i's ranking in city j
    for city_idx, city in enumerate(cities):
        city = city.replace(' ', '-').lower()
        city_link = f'https://www.shazam.com/charts/top-50/united-states/{city}'
        city_leaderboard = get_leaderboard(browser, city_link, url=True, get_song_meta=False)
        
        # join the city_leaderboard to find the rank of each song in that city
        merged_df = df.merge(city_leaderboard, on=['artist', 'song'], suffixes=('_main', '_city'))
        
        # get coordinates to update matrix
        song_indices = merged_df['id'].values
        matrix[song_indices, city_idx] = merged_df['rank_city'].values

    ranking_matrix_with_songid = np.concatenate((df['rank'].values.reshape(-1, 1), matrix), axis=1)
    ranking_df = pd.DataFrame(
        data=ranking_matrix_with_songid,
        columns=['song_id'] + cities
    )

    return ranking_df


# gets the number of shazams from a song link
def get_song_metadata(soup: BeautifulSoup):
    # get genre
    if soup.find('h3', {'class': 'genre'}):
        genre = soup.find('h3', {'class': 'genre'}).text.strip()
    else:
        genre = None

    # get the shazams and cast as int
    raw_shazams = soup.find('em', {'class': 'num'}).text
    shazams = int(''.join(raw_shazams.split(',')))

    return genre, shazams


def get_leaderboard(browser: webdriver.Chrome, source, top=None, url=True, get_song_meta=True):
    # Get page
    if url:
        soup = get_soup(browser, source)
    else:
        soup = source

    # create main dataframe
    items = soup.findAll('li', itemprop='track')

    if get_song_meta:
        df_dct = {
            'rank': [],
            'song': [],
            'artist': [],
            'genre': [],
            'shazams': []
        }
    else:
        df_dct = {
            'rank': [],
            'song': [],
            'artist': []
        }
    
    # loop through and scrape info for each item in leaderboard
    for item in items[:top]:
        number = item.find('div', {'class': 'number'}).text # get rank
        title = item.find('div', {'class': 'title'}).find('a')
        song_link = title['href']    # song link
        title = title.text  # song name
        artist = item.find('div', {'class': 'artist'}).text # artist name
        
        rank = int(number.strip())
        song_name = title.strip()
        artist = artist.strip()

        df_dct['rank'].append(rank)
        df_dct['song'].append(song_name)
        df_dct['artist'].append(artist)

        if get_song_meta:
            print(f'getting {song_name}')
            song_link = 'https://www.shazam.com' + song_link
            song_soup = get_soup(browser, song_link)
            genre, shazams = get_song_metadata(song_soup)
            df_dct['genre'].append(genre)
            df_dct['shazams'].append(shazams)

    # return dict
    return pd.DataFrame.from_dict(df_dct)    


def main():
    ## Setup chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--incognito")
    if headless:
        chrome_options.add_argument("--headless") # Ensure GUI is off

    # print('startings')
    # Choose Chrome Browser
    browser = webdriver.Chrome(options=chrome_options)

    # Get page
    main_leaderboard_url = "https://www.shazam.com/charts/top-200/united-states"
    discovery_url = "https://www.shazam.com/charts/discovery/united-states"
    main_soup = get_soup(browser, main_leaderboard_url)
    discovery_soup = get_soup(browser, discovery_url)

    # we can only get top 50 partitioned by city, so lets look at that
    main_leaderboard = get_leaderboard(browser, main_soup, top=top_songs, url=False, get_song_meta=True)
    discovery_leaderboard = get_leaderboard(browser, discovery_soup, url=False, get_song_meta=True)
    # main_leaderboard = pd.read_csv('main.csv')
    # discovery_leaderboard = pd.read_csv('discovery.csv')

    if save:
        discovery_leaderboard.to_csv('discovery.csv', index=False)
        main_leaderboard.to_csv('main.csv', index=False)

    # get movement of songs from leaderboard
    main_leaderboard['movement'] = main_leaderboard['rank'] / main_leaderboard['shazams']
    movings_songs = main_leaderboard.sort_values(by='movement', ascending=False).reset_index(drop=True).head(10)
    most_shazamd_songs = main_leaderboard.head(5)
    discovery_songs = main_leaderboard.merge(discovery_leaderboard, on=['artist', 'song', 'genre'], how='right')
    discovery_songs = discovery_songs.drop(['shazams_y', 'rank_y'], axis=1).rename(columns={'rank_x': 'rank', 'shazams_x': 'shazams'})

    # concat the above dfs into the "important songs" df
    important_songs = pd.concat((movings_songs, most_shazamd_songs, discovery_songs)).reset_index(drop=True)
    important_songs['id'] = np.arange(important_songs.shape[0])

    # get list of cities
    cities_dropdown = main_soup.find_all('div', attrs={'class': 'shz-simple-menu-items'})[1]
    raw_cities_list = cities_dropdown.find_all('div', attrs={'class': 'shz-simple-menu-item'})
    cities_list = [c.get_text().strip() for c in raw_cities_list]

    ranking_df = get_song_rank_by_city(browser, cities_list, important_songs)
    # ranking_df = pd.read_csv('song_rank_per_city.csv')
    browser.quit()


    if save:
        important_songs.to_csv('important.csv',index=False)
        ranking_df.to_csv('song_rank_per_city.csv', index=False)
    
    # find cities where song is performing best
    matrix = ranking_df.values
    cities_list = np.array(cities_list)

    cities_dct = {
        'song': [],
        'artist': [],
        'city': [],
        'city_rank': [],
        'general_rank': [],
        'difference': []
    }

    for i, row in enumerate(matrix):
        cities_popular_index = np.where(row == np.min(row))[0]

        song_name = important_songs['song'].values[i]
        artist_name = important_songs['artist'].values[i]
        row = row[1:]
        # print(song_name, len(cities_popular_index))

        if len(cities_popular_index) < cities_limit and len(cities_popular_index) > 0:
            main_rank = important_songs['rank'].values[i]
            city_rank = matrix[i, cities_popular_index[0]]
            cities = ', '.join(cities_list[cities_popular_index - 1])
            difference = main_rank - city_rank

            cities_dct['song'].append(song_name)
            cities_dct['artist'].append(artist_name)
            cities_dct['city'].append(cities)
            cities_dct['city_rank'].append(city_rank)
            cities_dct['difference'].append(difference)
            cities_dct['general_rank'].append(main_rank)

    cities_df = pd.DataFrame().from_dict(cities_dct)

    send_report(movings_songs, most_shazamd_songs, discovery_songs, cities_df)


if __name__ == '__main__':
    main()