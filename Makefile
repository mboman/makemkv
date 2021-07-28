build:
	docker build . -t mboman/makemkv

build-nocache:
	docker build . --no-cache -t mboman/makemkv

scan:
	docker scan mboman/makemkv

push:
	docker push mboman/makemkv
