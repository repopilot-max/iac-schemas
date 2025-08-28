# CFP IaC Validation Schemas

This repo is to hold schemas for validation with different tools like KCL or Kubconform

## Examples

---

```bash
$ kcl mod add --git https://gitlab.com/mxtechnologies/mx/architecture/cloud-infrastructure/cfp-iac-validation-schemas/schemas/kcl/argocd
```

```bash
$ kubeconform -schema-location 'https://gitlab.com/mxtechnologies/mx/architecture/cloud-infrastructure/cfp-iac-validation-schemas/schemas/json/argocd/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' -summary -output pretty <DIRECTORY_OF_YAML_MANIFESTS>
```
