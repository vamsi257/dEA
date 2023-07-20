max_page = 100


def page_limiter(count_img):
    print("Checking........................", count_img)
    if count_img >= max_page + 1:
        return True
    return False
