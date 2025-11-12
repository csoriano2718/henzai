NAME = henzai
VERSION = 0.1.0

.PHONY: all clean tarball srpm copr-build

all: tarball

clean:
	rm -rf $(NAME)-$(VERSION)/
	rm -f $(NAME)-$(VERSION).tar.gz
	rm -f $(NAME)-$(VERSION)-*.src.rpm

tarball:
	@echo "Creating tarball for version $(VERSION)..."
	mkdir -p $(NAME)-$(VERSION)
	
	# Copy daemon
	cp -r henzai-daemon $(NAME)-$(VERSION)/
	
	# Copy extension
	cp -r henzai-extension $(NAME)-$(VERSION)/
	
	# Copy documentation
	cp README.md LICENSE $(NAME)-$(VERSION)/
	
	# Create tarball
	tar czf $(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION)/
	
	@echo "Tarball created: $(NAME)-$(VERSION).tar.gz"
	@echo "Size: $$(du -h $(NAME)-$(VERSION).tar.gz | cut -f1)"

srpm: tarball
	@echo "Creating source RPM..."
	rpmbuild -bs \
		--define "_sourcedir $(PWD)" \
		--define "_srcrpmdir $(PWD)" \
		henzai.spec
	@echo "Source RPM created!"

copr-build: srpm
	@echo "Submitting to COPR..."
	copr-cli build csoriano/henzai $(NAME)-$(VERSION)-1.*.src.rpm
	@echo "Build submitted to https://copr.fedorainfracloud.org/coprs/csoriano/henzai/"

help:
	@echo "henzai RPM Build Targets:"
	@echo "  make tarball     - Create source tarball"
	@echo "  make srpm        - Create source RPM"
	@echo "  make copr-build  - Submit to COPR"
	@echo "  make clean       - Remove build artifacts"

