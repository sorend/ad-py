VER=$(shell git rev-parse --short HEAD)
REGISTRY=repo.treescale.com
IMAGE_NAME=$(REGISTRY)/sorend/adpy:$(VER)

none:
	@echo Please select target

dev:
	docker run --rm -it -p 8080:8080 $(IMAGE_NAME)

deploy:
	# setup kubeconfig
	kubectl apply -f k8s.yml

release:
	docker login --username $(HUB_USERNAME) --password $(HUB_SECRET) $(REGISTRY)
	docker push $(IMAGE_NAME)

build:
	docker build -t $(IMAGE_NAME) .
