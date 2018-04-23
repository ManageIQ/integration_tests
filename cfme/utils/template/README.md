Available providers:

    ec2
    gce
    openstack
    openshift
    rhevm
    scvmm
    virtualcenter



Required arguments:

    --provider PROVIDER_NAME
        OR
    --provider-type PROVIDER_TYPE
        IGNORED WHEN --provider is used

Optional arguments:

    --stream CUSTOM_STREAM_NAME
        REQUIRES --stream-url if stream name is not listed in cfme_data

    --stream-url CUSTOM_URL_TO_STREAM_DIRECTORY
        REQUIRES --stream

    --image-url URL_PATH_TO_IMAGE_FILE

    --template-name CUSTOM_TEMPLATE_NAME
        if template name is used -> template will be formatted as {template}-{stream}
    
    --print-name-only
        Prints template names and exits.

Usage example:

    $ python template_upload.py --provider rhos11 --template-name test-upload --stream downstream-59z
    Uploads template on RHOS11 provider using downstream-59z with name test-upload-downstream-59z

    $ python template_upload.py --provider-type openstack --stream upstream
    Upload template from upstream on every available Openstack provider

    $ python template_upload.py --provider scvmm2016
    Upload templates from every available stream on SCVMM2016 provider
