build:
	docker build -t registry.home.exphost.pl/exphost/template-renderer .

push:
	docker push registry.home.exphost.pl/exphost/template-renderer

run:
	docker run -it registry.home.exphost.pl/exphost/template-renderer
