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

But I also don't agree with that structure. First off all there is no need for "book_slug" field. That would make sense if I had LOTS of books like thousands, hundrets of them - not 40. Then sure I would want to have field that is unchanged and nothing will break if i change the title. But in my case it is not nedeed in my opininon. On top of that source_url also will not be used by anything in this software. There is no method, endpoint, function anything that will use that.

After reconsideration I tought that I will go with this structure:

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

But actually i tought that maybe I will use regular SQL database with pgvector extention. Without payload and just regular columns I can not only make vector search but also normal one using SQL queries - which I will need later on.   So this was the first approach of how the database looked like: 

| id                  | title           | author          | fragment                    | chunk_index | location                              | embedding                                        |
| ------------------- | --------------- | --------------- | ---------------------------- | ----------- | -------------------------------------- | ------------------------------------------------- |
| dziady_cz_iii_0001  | Dziady cz. III  | Adam Mickiewicz | Something something lorem ipsum... | 67          | {"page": 2, "char_range": [0, 2213]} | [0.0145787215, 0.017090317, -0.018824786, 0.01253039 ...] ||

But there was again - another issue. Model could not find the right fragments of books the user was asking about. The semantic search alone was not giving satisfying results - and that is when I reinvented the wheel.

And when I had not idea I asked Claude something like - "Is it a good idea to store hypothetical questions of students in the database and assign chunks to them? So whenever student asks about something simmilar i already have anwser to It will retrive just that chunk?" - and it told me to do research about "Hypothetical Prompt Embeddings". 

```txt
"The name that best fits what you described is HyPE: instead of embedding document chunks, it generates multiple hypothetical queries per chunk during the indexing stage, and user queries are matched against these stored hypothetical questions—thereby avoiding the generation of a synthetic answer at query time, reducing computational overhead, and improving matching accuracy. This is the exact opposite of HyDE (hence the name) and appears to be the most accurate description of your idea."
```

So I knew I **absolutely** have to try this.

## Chunking and inserting chunks into database

AI suggested that the best approach is to use OCR when standard ways of parsing a pdf will fail (due to weird formatting). So i did try this, but formatting was even worse (I used easy ocr library) - every word had its own line (in other words, every word was in diffrent line of the file). I decided to google other ways of extracting data from pdf's, found the docs and delegated this task to AI to code it for me. But there still was something off about it. The tesseract OCR worked cool but it did not preserve the formatting of the page. And I did not know how complicated it would be to make algorithm that would do that. So I thought that I will go with some small local model, fine tuned to OCR task that will preserve the formating. 

#### stages of extracting data from the books
1. data preparation
    - I iterate through every pdf, convert it to photos and request local ocr model with that photo and simple prompt.
    ```txt
        "Extract the text from the page of this book. "
        "Keep the formatting just as it is in the page. "
        "Do not return anything else except this text."
    ``` 
    - Save the extracted text to one big json file - don't worry its temporary 
    - Iterate through the file and chunk the books into even fragments + embedding them 
    - Iterate through the chunks and make local LLM model make hypothetical questions to those fragments (and those questions will be inserted later into diffrent table)
2. data inserting - basically inserting everything that was extracted into local docker database so far.






