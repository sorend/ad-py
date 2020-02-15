VER=$(shell git rev-parse --short HEAD)
REGISTRY=repo.treescale.com
IMAGE_NAME=$(REGISTRY)/sorend/adpy:$(VER)

none:
	@echo Please select target

dev:
	docker run --rm -it -p 8080:8080 $(IMAGE_NAME)

deploy:
	cat k8s.yml | sed -e "s/VERSION/$(VER)/g" > k8s-versioned.yml
	cat k8s-versioned.yml
	kubectl apply -f adpy-secret.yml -n default
	kubectl apply -f k8s-versioned.yml -n default

release:
	echo $(HUB_PASSWORD) | docker login --username $(HUB_USERNAME) --password-stdin $(REGISTRY)
	docker push $(IMAGE_NAME)

build:
	docker build -t $(IMAGE_NAME) .
