import json
import os
from contextlib import contextmanager

from pixivpy3 import PixivAPI, AppPixivAPI, PixivError
from pixivpy3.api import BasePixivAPI
# noinspection PyUnresolvedReferences, PyPackageRequirements
from secret import (
    USERNAME, PASSWORD,
    USERNAME_NO_R18, PASSWORD_NO_R18,
    REQUEST_KWARGS,
)

ILLUST_ID = 73011378
ILLUST_MULTI_PAGE_ID = 72922398
MANGA_ID = 72821333
MANGA_SINGLE_PAGE_ID = 72910866
UGOIRA_ID = 72857773

BAD_ILLUST_ID = 9999999999999
R18_ILLUST_ID = 73030422
R18G_ILLUST_ID = 74693586

SERIES_ILLUST_ID = 74667649

QUERY = 'オリジナル'

USER_ID = 3188698
BAD_USER_ID = 9999999999999

DATE_WITH_UGOIRA = '2019-02-07'
BAD_DATE = '2099-01-01'

SHOWCASE_ID = 4115
BAD_SHOWCASE_ID = 999999

ILLUST_TYPE_ID_DICT = {
    'illust': ILLUST_ID,
    'illust_multi_page': ILLUST_MULTI_PAGE_ID,
    'illust_r18': R18_ILLUST_ID,
    'illust_r18g': R18G_ILLUST_ID,
    'illust_series': SERIES_ILLUST_ID,
    'manga': MANGA_ID,
    'manga_single_page': MANGA_SINGLE_PAGE_ID,
    'ugoira': UGOIRA_ID,
}


def save_json(json_result, filename):
    if not filename.lower().endswith('.json'):
        filename = filename + '.json'
    with open(filename, 'wt', encoding='utf-8') as f:
        json.dump(json_result, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(os.path.relpath(
        os.path.abspath(filename),
        os.path.dirname(__file__),
    ))


@contextmanager
def work_path(path):
    cwd = os.getcwd()
    os.makedirs(path, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def test_base_api():
    api = BasePixivAPI(**REQUEST_KWARGS)

    json_result = api.login(USERNAME, PASSWORD)
    json_result['response']['user']['account'] = 'user_abcd1234'
    json_result['response']['user']['id'] = 99999999
    json_result['response']['user']['mail_address'] = 'foo@bar.com'
    json_result['response']['user']['name'] = 'Name'
    for key in json_result['response']:
        if key.endswith('_token'):
            json_result['response'][key] = '1234567890'
    save_json(json_result, 'login')

    try:
        api.login('user@foo.bar', 'password')
    except PixivError as e:
        json_result = api.parse_json(e.body)
        save_json(json_result, 'login - bad_username_password')

    json_result = api.auth()
    json_result['response']['user']['account'] = 'user_abcd1234'
    json_result['response']['user']['id'] = 99999999
    json_result['response']['user']['mail_address'] = 'foo@bar.com'
    json_result['response']['user']['name'] = 'Name'
    for key in json_result['response']:
        if key.endswith('_token'):
            json_result['response'][key] = '1234567890'
    save_json(json_result, 'auth')

    try:
        api.auth(refresh_token='bad_token')
    except PixivError as e:
        json_result = api.parse_json(e.body)
        save_json(json_result, 'auth - bad_refresh_token')


def test_public_api():
    api = PixivAPI(**REQUEST_KWARGS)
    api.login(USERNAME, PASSWORD)

    # ================
    api.access_token = 'bad_token'
    json_result = api.works(ILLUST_ID)
    save_json(json_result, '[expired]')
    api.auth()

    # ================
    # decrypted
    json_result = api.bad_words()
    save_json(json_result, 'bad_words')

    # ================
    for illust_type, illust_id in ILLUST_TYPE_ID_DICT.items():
        json_result = api.works(illust_id)
        save_json(json_result, 'works - {}'.format(illust_type))

    json_result = api.works(BAD_ILLUST_ID)
    save_json(json_result, 'works - bad_illust_id')

    api_no_r18 = PixivAPI(**REQUEST_KWARGS)
    api_no_r18.login(USERNAME_NO_R18, PASSWORD_NO_R18)
    json_result = api_no_r18.works(R18_ILLUST_ID)
    save_json(json_result, 'works - r18_restricted')
    del api_no_r18

    # ================
    json_result = api.users(USER_ID)
    save_json(json_result, 'users')

    json_result = api.users(BAD_USER_ID)
    save_json(json_result, 'users - bad_user_id')

    # ================
    # decrypted
    json_result = api.me_feeds()
    save_json(json_result, 'me_feeds')

    # ================
    # decrypted
    json_result = api.me_favorite_works()
    save_json(json_result, 'me_favorite_works')

    # ================
    # decrypted
    json_result = api.me_favorite_works_add(ILLUST_ID)
    save_json(json_result, 'me_favorite_works_add')

    json_result = api.me_favorite_works_add(ILLUST_ID)
    save_json(json_result, 'me_favorite_works_add - added')

    json_result = api.me_favorite_works_add(BAD_ILLUST_ID)
    save_json(json_result, 'me_favorite_works_add - bad_illust_id')

    # ================
    # decrypted
    json_result = api.me_favorite_works_delete(ILLUST_ID)
    save_json(json_result, 'me_favorite_works_delete')

    json_result = api.me_favorite_works_delete(ILLUST_ID)
    save_json(json_result, 'me_favorite_works_delete - deleted')

    json_result = api.me_favorite_works_delete(BAD_ILLUST_ID)
    save_json(json_result, 'me_favorite_works_delete - bad_illust_id')

    # ================
    json_result = api.me_following_works()
    save_json(json_result, 'me_following_works')

    while json_result['pagination']['next']:
        json_result = api.me_following_works(
            page=json_result['pagination']['next'],
        )
    save_json(json_result, 'me_following_works - last_page')

    # ================
    json_result = api.me_following()
    save_json(json_result, 'me_following')

    # ================
    json_result = api.me_favorite_users_follow(USER_ID)
    save_json(json_result, 'me_favorite_users_follow')

    json_result = api.me_favorite_users_follow(USER_ID)
    save_json(json_result, 'me_favorite_users_follow - followed')

    json_result = api.me_favorite_users_follow(BAD_USER_ID)
    save_json(json_result, 'me_favorite_users_follow - bad_user_id')

    # ================
    json_result = api.me_favorite_users_unfollow(USER_ID)
    save_json(json_result, 'me_favorite_users_unfollow')

    json_result = api.me_favorite_users_unfollow(USER_ID)
    save_json(json_result, 'me_favorite_users_unfollow - unfollowed')

    json_result = api.me_favorite_users_unfollow(BAD_USER_ID)
    save_json(json_result, 'me_favorite_users_unfollow - bad_user_id')

    # ================
    json_result = api.users_works(USER_ID)
    save_json(json_result, 'users_works')

    json_result = api.users_works(BAD_USER_ID)
    save_json(json_result, 'users_works - bad_user_id')

    # ================
    json_result = api.users_favorite_works(USER_ID)
    save_json(json_result, 'users_favorite_works')

    json_result = api.users_favorite_works(BAD_USER_ID)
    save_json(json_result, 'users_favorite_works - bad_user_id')

    # ================
    json_result = api.users_feeds(USER_ID)
    save_json(json_result, 'users_feeds')

    json_result = api.users_feeds(BAD_USER_ID)
    save_json(json_result, 'users_feeds - bad_user_id')

    # ================
    json_result = api.users_following(USER_ID)
    save_json(json_result, 'users_following')

    json_result = api.users_following(BAD_USER_ID)
    save_json(json_result, 'users_following - bad_user_id')

    # ================
    json_result = api.ranking()
    save_json(json_result, 'ranking')

    json_result = api.ranking(mode='manga')
    save_json(json_result, 'ranking - manga')

    json_result = api.ranking(mode='ugoira')
    save_json(json_result, 'ranking - ugoira')

    json_result = api.ranking(date=BAD_DATE)
    save_json(json_result, 'ranking - bad_date')

    # ================
    json_result = api.search_works(QUERY, mode='exact_tag')
    save_json(json_result, 'search_works')

    json_result = api.search_works(QUERY, mode='exact_tag', order='asc')
    save_json(json_result, 'search_works - asc_order')

    json_result = api.search_works(QUERY, mode='exact_tag', types=['manga'])
    save_json(json_result, 'search_works - manga')

    json_result = api.search_works(QUERY, mode='exact_tag', types=['ugoira'])
    save_json(json_result, 'search_works - ugoira')

    # ================
    json_result = api.latest_works()
    save_json(json_result, 'latest_works')


def test_app_api():
    api = AppPixivAPI(**REQUEST_KWARGS)
    api.login(USERNAME, PASSWORD)

    # ================
    api.access_token = 'bad_token'
    json_result = api.illust_detail(ILLUST_ID)
    save_json(json_result, '[expired]')
    api.auth()

    # ================
    json_result = api.user_detail(USER_ID)
    save_json(json_result, 'user_detail')

    json_result = api.user_detail(BAD_USER_ID)
    save_json(json_result, 'user_detail - bad_user_id')

    # ================
    json_result = api.user_illusts(USER_ID)
    save_json(json_result, 'user_illusts')

    json_result = api.user_illusts(BAD_USER_ID)
    save_json(json_result, 'user_illusts - bad_user_id')

    # ================
    json_result = api.user_bookmarks_illust(USER_ID)
    save_json(json_result, 'user_bookmarks_illust')

    json_result = api.user_bookmarks_illust(BAD_USER_ID)
    save_json(json_result, 'user_bookmarks_illust - bad_user_id')

    # ================
    json_result = api.illust_follow()
    save_json(json_result, 'illust_follow')

    next_qs = api.parse_qs(json_result.next_url)
    while next_qs is not None:
        json_result = api.illust_follow(**next_qs)
        next_qs = api.parse_qs(json_result.next_url)
    save_json(json_result, 'illust_follow - last_page')

    # ================
    for illust_type, illust_id in ILLUST_TYPE_ID_DICT.items():
        json_result = api.illust_detail(illust_id)
        save_json(json_result, 'illust_detail - {}'.format(illust_type))

    json_result = api.illust_detail(BAD_ILLUST_ID)
    save_json(json_result, 'illust_detail - bad_illust_id')

    api_no_r18 = AppPixivAPI(**REQUEST_KWARGS)
    api_no_r18.login(USERNAME_NO_R18, PASSWORD_NO_R18)
    json_result = api_no_r18.illust_detail(R18_ILLUST_ID)
    save_json(json_result, 'illust_detail - r18_restricted')
    del api_no_r18

    # ================
    json_result = api.illust_comments(ILLUST_ID)
    save_json(json_result, 'illust_comments')

    json_result = api.illust_comments(BAD_ILLUST_ID)
    save_json(json_result, 'illust_comments - bad_illust_id')

    api_no_r18 = AppPixivAPI(**REQUEST_KWARGS)
    api_no_r18.login(USERNAME_NO_R18, PASSWORD_NO_R18)
    json_result = api_no_r18.illust_comments(R18_ILLUST_ID)
    save_json(json_result, 'illust_comments - r18_restricted')
    del api_no_r18

    # ================
    json_result = api.illust_related(ILLUST_ID)
    save_json(json_result, 'illust_related')

    json_result = api.illust_related(BAD_ILLUST_ID)
    save_json(json_result, 'illust_related - bad_illust_id')

    api_no_r18 = AppPixivAPI(**REQUEST_KWARGS)
    api_no_r18.login(USERNAME_NO_R18, PASSWORD_NO_R18)
    json_result = api_no_r18.illust_related(R18_ILLUST_ID)
    save_json(json_result, 'illust_related - r18_restricted')
    del api_no_r18

    # ================
    json_result = api.illust_recommended()
    save_json(json_result, 'illust_recommended')

    # ================
    json_result = api.illust_ranking()
    save_json(json_result, 'illust_ranking')

    json_result = api.illust_ranking(mode='day_manga')
    save_json(json_result, 'illust_ranking - day_manga')

    json_result = api.illust_ranking(date=DATE_WITH_UGOIRA)
    save_json(json_result, 'illust_ranking - date_with_ugoira')

    json_result = api.illust_ranking(date=BAD_DATE)
    save_json(json_result, 'illust_ranking - bad_date')

    # ================
    json_result = api.trending_tags_illust()
    save_json(json_result, 'trending_tags_illust')

    # ================
    json_result = api.search_illust(QUERY, search_target='exact_match_for_tags')
    save_json(json_result, 'search_illust')

    json_result = api.search_illust(
        QUERY,
        search_target='exact_match_for_tags',
        sort='date_asc',
    )
    save_json(json_result, 'search_illust - asc_order')

    json_result = api.search_illust('漫画', search_target='exact_match_for_tags')
    save_json(json_result, 'search_illust - manga')

    json_result = api.search_illust(
        'うごイラ',
        search_target='exact_match_for_tags',
    )
    save_json(json_result, 'search_illust - ugoira')

    # ================
    json_result = api.illust_bookmark_detail(ILLUST_ID)
    save_json(json_result, 'illust_bookmark_detail')

    json_result = api.illust_bookmark_detail(BAD_ILLUST_ID)
    save_json(json_result, 'illust_bookmark_detail - bad_illust_id')

    api_no_r18 = AppPixivAPI(**REQUEST_KWARGS)
    api_no_r18.login(USERNAME_NO_R18, PASSWORD_NO_R18)
    json_result = api_no_r18.illust_bookmark_detail(R18_ILLUST_ID)
    save_json(json_result, 'illust_bookmark_detail - r18_restricted')
    del api_no_r18

    # ================
    json_result = api.illust_bookmark_add(ILLUST_ID)
    save_json(json_result, 'illust_bookmark_add')

    json_result = api.illust_bookmark_add(ILLUST_ID)
    save_json(json_result, 'illust_bookmark_add - added')

    json_result = api.illust_bookmark_add(BAD_ILLUST_ID)
    save_json(json_result, 'illust_bookmark_add - bad_illust_id')

    # ================
    json_result = api.illust_bookmark_delete(ILLUST_ID)
    save_json(json_result, 'illust_bookmark_delete')

    json_result = api.illust_bookmark_delete(ILLUST_ID)
    save_json(json_result, 'illust_bookmark_delete - deleted')

    json_result = api.illust_bookmark_delete(BAD_ILLUST_ID)
    save_json(json_result, 'illust_bookmark_delete - bad_illust_id')

    # ================
    json_result = api.user_bookmark_tags_illust()
    save_json(json_result, 'user_bookmark_tags_illust')

    # ================
    json_result = api.user_following(USER_ID)
    save_json(json_result, 'user_following')

    json_result = api.user_following(BAD_USER_ID)
    save_json(json_result, 'user_following - bad_user_id')

    # ================
    json_result = api.user_follower(USER_ID)
    save_json(json_result, 'user_follower')

    json_result = api.user_follower(BAD_USER_ID)
    save_json(json_result, 'user_follower - bad_user_id')

    # ================
    # unknown usage
    json_result = api.user_mypixiv(USER_ID)
    save_json(json_result, 'user_mypixiv')

    json_result = api.user_mypixiv(BAD_USER_ID)
    save_json(json_result, 'user_mypixiv - bad_user_id')

    # ================
    # unknown usage
    json_result = api.user_list(USER_ID)
    save_json(json_result, 'user_list')

    json_result = api.user_list(BAD_USER_ID)
    save_json(json_result, 'user_list - bad_user_id')

    # ================
    json_result = api.ugoira_metadata(UGOIRA_ID)
    save_json(json_result, 'ugoira_metadata')

    json_result = api.ugoira_metadata(MANGA_ID)
    save_json(json_result, 'ugoira_metadata - manga_id')

    json_result = api.ugoira_metadata(BAD_ILLUST_ID)
    save_json(json_result, 'ugoira_metadata - bad_illust_id')

    # ================
    json_result = api.showcase_article(SHOWCASE_ID)
    save_json(json_result, 'showcase_article')

    json_result = api.showcase_article(BAD_SHOWCASE_ID)
    save_json(json_result, 'showcase_article - bad_showcase_id')


def main():
    with work_path('Base API'):
        test_base_api()

    with work_path('PixivAPI'):
        test_public_api()

    with work_path('AppPixivAPI'):
        test_app_api()


if __name__ == '__main__':
    main()
