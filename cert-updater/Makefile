deploy:
	docker login --username iam --password $(YC_TOKEN) cr.yandex
	docker build -t cert-updater --network host .
	docker tag cert-updater cr.yandex/$(REGISTRY_ID)/cert-updater
	docker push cr.yandex/$(REGISTRY_ID)/cert-updater
	yc serverless container revision deploy \
		--container-name cert-updater \
		--image cr.yandex/$(REGISTRY_ID)/cert-updater \
		--cores 1 \
		--memory 2GB \
		--concurrency 1 \
		--execution-timeout 600s \
		--service-account-id $(SERVICE_ACCOUNT_ID) \
		--network-id $(NETWORK_ID) \
		--environment DNS_ZONE_ID=$(DNS_ZONE_ID),CERTIFIATE_FOLDER_ID=$(CERTIFIATE_FOLDER_ID)
