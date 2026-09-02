from forza_picker.wiki_images import (
    get_wiki_image_url,
    get_or_download_wiki_image,
)


def main():
    image_url = get_wiki_image_url(
        "File:FH6 Abarth 595 esseesse.png"
    )

    if image_url is None:
        print("Image URL not found")
        return

    image_path = get_or_download_wiki_image(
        "File:FH6 Abarth 595 esseesse.png",
    )

    print(f"Image path: {image_path}")


if __name__ == "__main__":
    main()