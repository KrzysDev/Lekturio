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



