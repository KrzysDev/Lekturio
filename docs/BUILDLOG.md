# What is BUILDLOG.md?

## Purpose

This file documents a very important aspect of building software with 
AI assistance: the **4D framework** — Delegation, Description, 
Discernment, Diligence.

It records where AI was used, where it helped, where it fell short, 
and where I chose to write things myself instead. This isn't just a 
"fun fact" page — it helps future contributors, Flyrank Internship 
evaluators, and anyone else reviewing this project understand *what* 
was done, *how* it was done, and *where AI fit into the process*.


# Notes:

## The research
When I was talking with Claude about the project it found something very interesting - site called "Wolne Lektury" (Free Set Books) containg lots of books not only from polish literature but also the wolrd one shares their api. By this API i can access every book I need without the need of scraping website or manually downloading every pdf. Using this information I asked Claude to write me a simple script that will download all the books I need.

File doing that can be found in ```/src/lekturio/tools/book_collector.py```. The goal of the file is to download every book on my desktop, then i will be able to iterate through the pdfs, chunk them and insert those chunks into vector database.

## The JSON structure
I have to use JSON structure for payload in vector database. It is very important how this payload will be structured because it will be embedded and then retrived by the LLM.
Firstly i came up with something like this:

```json
{
    "id" : uuid,
    "lektura" : "Lalka"
    "metadane" : {
        "rozdział" : 2,
        "strona" : 198,
        "wektor" : [1, 0.1.....]
        "char_range" : [11411, 25444]
    }

    "fragment" : [
        "something something something lorem ipsum lorem ipsum"
    ]
    "autor" : "Bolesław Prus"
}
```

After brainstorming my idea with AI i saw that structure I came up with was not really a good idea. Firstly - there is no need to store vector in the payload (I dont know why i did that), secondly it can be much more simplified. Thats what Claude gave me:

```json
    {
        "id": "lalka_0042",
        "book_slug": "lalka",
        "title": "Lalka",
        "author": "Bolesław Prus",
        "fragment": "Wokulski spojrzał na Izabelę i poczuł...",
        "chunk_index": 42,
        "location": {
                "chapter": "Tom I, rozdział 3",
                "char_range": [12400, 12850]
            },
        "source_url": "https://wolnelektury.pl/media/book/txt/lalka.txt"
    }
```

But I also don't agree with that structure. First off all there is no need for "book_slug" field. That would make sens if I had LOTS of books like thousands, hundrets of them - not 40. Then sure I would want to have field that is unchanged and nothing will break if i change the title. But in my case it is not nedeed in my opininon. On top of that source_url also will not be used by anything in this software. There is no method, endpoint, function anything that will use that.

After reconsideration i will go with this structure:

```json
    {
        "id": "lalka_0042",
        "title": "Lalka",
        "author": "Bolesław Prus",
        "fragment": "Wokulski spojrzał na Izabelę i poczuł...",
        "chunk_index": 42,
        "location": {
                "page": 129,
                "char_range": [12400, 12850]
            }
    }
```

## Chunking and inserting chunks into database

AI suggested that the best approach is to use OCR when standard ways of parsing a pdf will fail (due to weird formatting). So i did try this, but formatting was even worse - every word had its own line (in other words, every word was in diffrent line of the file). I decided to google other ways of extracting data from pdf's, found the docs and delegated this task to AI to code it for me. I want to be honest - for now i do not know how to do it better. The formating sometimes breaks but i hope it will not affect retrival that much.




