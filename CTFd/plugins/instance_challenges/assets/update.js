CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$;

    function loadImages(selectedValue) {
        const $select = $("#instance_image");
        fetch(CTFd.config.urlRoot + "/admin/instances/images", {
            method: "GET",
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        })
            .then((res) => res.json())
            .then((data) => {
                const images = (data && data.images) || [];
                $select.empty();
                // Ensure the currently-saved image is always selectable, even
                // if it was later removed from the allow-list.
                if (selectedValue && images.indexOf(selectedValue) === -1) {
                    images.unshift(selectedValue);
                }
                if (images.length === 0) {
                    $select.append(
                        '<option value="">— No images configured (Admin → Instances) —</option>'
                    );
                    return;
                }
                $select.append('<option value="">— Select an image —</option>');
                images.forEach((img) => {
                    const sel = img === selectedValue ? " selected" : "";
                    $select.append(
                        '<option value="' + img + '"' + sel + ">" + img + "</option>"
                    );
                });
            })
            .catch(() => {
                $select.empty();
                if (selectedValue) {
                    $select.append(
                        '<option value="' + selectedValue + '" selected>' +
                        selectedValue + "</option>"
                    );
                } else {
                    $select.append('<option value="">— Failed to load images —</option>');
                }
            });
    }

    loadImages($("#instance_image").data("selected"));
});
