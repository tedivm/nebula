# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure("2") do |config|

  config.vm.box = "ubuntu/xenial64"
  config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network "forwarded_port", guest: 5000, host: 5000
  config.vm.provision "shell", path: "provisioning/vagrant_setup.sh"

  config.vm.provider "virtualbox" do |v|
    # Two gigs are needed during the first run to process the aws service file.
    # After that it only takes a couple of minutes.
    v.memory = 2048
  end

end
