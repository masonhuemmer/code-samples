#---------------------------------------------------
# RESOURCES 
#---------------------------------------------------

resource "azurerm_resource_group" "default" {

  name     = "${var.global.company_code}-${var.global.product_code}-${var.global.env_code}"
  location = var.global.location

}

#---------------------------------------------------
# MODULES 
#---------------------------------------------------

module "alphago_network_service" {

  source  = "app.terraform.io/masonhuemmer/alphago-network-service/azurerm"
  version = "1.0.0"

  # GLOBAL OBJECT
  global  = merge(var.global, {
    "resource_group_name" = azurerm_resource_group.default.name
    "location"            = azurerm_resource_group.default.location
    "service_code"        = "VNET"
  })

  # NETWORK OBJECT
  network = var.network

}