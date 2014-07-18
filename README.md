# Machete

Basic proof of concept of JSON API in Django.

Uses [Marshmallow](http://marshmallow.readthedocs.org/en/latest/) (v0.7.0)
for serialization and basic Django class-based views to implement at least part of the JSON API spec.


## Installation

First, get the source. Then:

    $ mkvirtualenv jsonapi
    ...
    $ pip install marshmallow==0.7.0
    ...
    $ pip install Django==1.6.5
    ...
    $ cd blogger

Then either run:

    $ python manage.py syncdb
    ...

Or rename db.sqlite3.example to db.sqlite3:

    $ cp db.sqlite3.example db.sqlite3

Finally start the server:

    $ python manage.py runserver

Play around with it ([HTTPie](https://github.com/jakubroztocil/httpie) is recommended) by opening [http://localhost:8000/api/posts]()

Seed data (run `python manage.py shell` and paste the code below):

    from blog.models import *
    kevin = Person(name='Kevin')
    kevin.save()
    bart = Person(name='Bart')
    bart.save()
    timmy = Person(name='Timmy')
    timmy.save()
    tag_django = Tag(name='django')
    tag_django.save()
    tag_json = Tag(name='json')
    tag_json.save()
    tag_random = Tag(name='random')
    tag_random.save()
    introducing_machete = Post(title='Introducing Machete')
    introducing_machete.content = "Today we're happy to announce the release of version 1.0 of Machete, a toolkit to provide JSON API compliant endpoints in Django."
    introducing_machete.author = kevin
    introducing_machete.save()
    introducing_machete.tags = [tag_django, tag_json]
    machete_bugfix = Post(title='Machete bugfix released')
    machete_bugfix.author = bart
    machete_bugfix.content = "A bugfix for Machete has been released. Get version 1.0.1 now!"
    machete_bugfix.save()
    machete_bugfix.tags = [tag_json]
    too_long = Post(title="It's been a long time")
    too_long.author = timmy
    too_long.content = "Well, it's been a while since this blog saw an update..."
    too_long.save()
    too_long.tags = [tag_random]
    welcome = Post(title='Welcome to our blog!')
    welcome.author = kevin
    welcome.content = "Enjoy your stay!"
    welcome.save()
    comment = Comment(author=timmy)
    comment.content = "First!"
    comment.post = welcome
    comment.save()
    comment = Comment(author=bart, approved=True)
    comment.content = "Go, go, go!"
    comment.post = welcome
    comment.save()
    comment = Comment(author=kevin, approved=True)
    comment.content = "Great, thanks!"
    comment.post = machete_bugfix
    comment.save()
    comment = Comment(author=kevin, approved=True)
    comment.content = "BTW, seems like there's another issue..."
    comment.post = machete_bugfix
    comment.save()
    comment = Comment(commenter='vi4gr4', content='Get it here')
    comment.post = machete_bugfix
    comment.save()


## TO DO

- [Updating relationships](http://jsonapi.org/format/#crud-updating-relationships)
- [Decent errors](http://jsonapi.org/format/#errors)
- [PATCH support](http://jsonapi.org/format/#patch)
- [HTTP Caching](http://jsonapi.org/format/#http-caching)
- Fixing passing of context to nested serializers in marshmallow
