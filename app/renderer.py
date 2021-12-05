#!/usr/bin/env python
import kopf
import kubernetes
import jinja2
import base64
from prometheus_client import start_http_server

@kopf.on.resume('exphost.pl','v1','templates')
@kopf.on.create('exphost.pl','v1','templates')
@kopf.on.update('exphost.pl','v1','templates')
@kopf.timer('exphost.pl','v1','templates', interval=60.0)
def create_fn(body, spec, name, namespace ,logger, **kwargs):
    logger.info(f"template creates: {body}")
    api = kubernetes.client.CoreV1Api()
    values = {}
    for val in spec['values']:
        logger.info(f"looking for: {val}")
        if val['source_type'] == "ConfigMap":
            source = api.read_namespaced_config_map(val['source_name'], namespace)
            values[val['name']] = source.data[val['source_key']]
        elif val['source_type'] == "Secret":
            source = api.read_namespaced_secret(val['source_name'], namespace)
            values[val['name']] = base64.b64decode(source.data[val['source_key']]).decode()
    logger.info(f"got values: {values}")
    if spec['destination_type'] == "ConfigMap":
        dest_obj = kubernetes.client.V1ConfigMap
        list_func = api.list_namespaced_config_map
        read_func = api.read_namespaced_config_map
        replace_func = api.replace_namespaced_config_map
        create_func = api.create_namespaced_config_map
        def hash(data):
            return data
    elif spec['destination_type'] == "Secret":
        dest_obj = kubernetes.client.V1Secret
        list_func = api.list_namespaced_secret
        read_func = api.read_namespaced_secret
        replace_func = api.replace_namespaced_secret
        create_func = api.create_namespaced_secret
        def hash(data):
            return base64.b64encode(data.encode()).decode()
    data = {}
    manifest= {
        'namespace': namespace,
        'body': dest_obj(
            metadata=kubernetes.client.V1ObjectMeta(
                name=spec['destination_name'],
                labels=spec.get('destination_labels', {}),
                annotations=spec.get('destination_annotations', {}),
            ),
            data={key: hash(jinja2.Template(template).render(values)) for key, template in spec['templates'].items()},
        )
    }
    kopf.append_owner_reference(manifest['body'])
    if len(list(filter(lambda x: x.metadata.name == spec['destination_name'], list_func(namespace).items))):
        logger.info("{type} {name} exists".format(type=spec['destination_type'], name=spec['destination_name']))
        bo = read_func(spec['destination_name'], namespace)
        different = (bo.data != manifest['body'].data)
        logger.info("Diff? {diff}".format(diff=different))
        if different:
            logger.info("replace {type} {name}".format(type=spec['destination_type'], name=spec['destination_name']))
            replace = replace_func(spec['destination_name'], namespace, manifest['body'])
    else:
        logger.info("creating {type} {name}".format(type=spec['destination_type'], name=spec['destination_name']))
        logger.info("manifest: {manifest}".format(manifest=manifest))
        create_func(**manifest)
            

start_http_server(8000)
