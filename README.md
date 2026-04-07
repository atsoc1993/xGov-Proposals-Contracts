# xGov Proposal's Contracts

This repository contains the contracts that will be open-sourced to assist with meeting terms and conditions. Although it is not ideal we understand that the xGov council will be more comfortable in seeing the contracts ahead of time.

**Note: We are not including testing files, codebases, full documentation, or references to any infrastructure used for these contracts. This is SOLELY to gauge the authenticity of claimed work completed. More verbose documentation can be added upon proposal approval**

## Proof of Compilation (Compile Commands)

From the root folder, all of the contracts can be compiled with respective commands, see bottom of README for an aggregated command

### Algofun Shares System

**TEAL, Mapping & ARC56 Json**

**Linux**  
`algokit compile py 'Algofun Shares System Contract/shares_system_contract.py' --output-arc56 --out-dir generated_contract_files`

**PowerShell**  
`algokit compile py 'Algofun Shares System Contract\shares_system_contract.py' --output-arc56 --out-dir generated_contract_files`

**Client**

**Linux**  
`algokitgen-py -a 'Algofun Shares System Contract/generated_contract_files/AlgofunSharesSystem.arc56.json' -o 'Algofun Shares System Contract/generated_contract_files/shares_client.py'`

**PowerShell**  
`algokitgen-py -a 'Algofun Shares System Contract\generated_contract_files\AlgofunSharesSystem.arc56.json' -o 'Algofun Shares System Contract\generated_contract_files\shares_client.py'`

### AVM Email Contracts

**TEAL, Mapping & ARC56 Json**

**Linux**  
`algokit compile py 'AVM Email Contracts/avm_email_contracts.py' --output-arc56 --out-dir generated_contract_files`

**PowerShell**  
`algokit compile py 'AVM Email Contracts\avm_email_contracts.py' --output-arc56 --out-dir generated_contract_files`

**Clients**

**Linux**
```
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/EmailRegistry.arc56.json' -o 'AVM Email Contracts/generated_contract_files/registry_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/ServerContract.arc56.json' -o 'AVM Email Contracts/generated_contract_files/server_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/EmailContract.arc56.json' -o 'AVM Email Contracts/generated_contract_files/email_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/SpamEmail.arc56.json' -o 'AVM Email Contracts/generated_contract_files/spam_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/EmailListings.arc56.json' -o 'AVM Email Contracts/generated_contract_files/marketplace_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/PrivateStakingPoolManager.arc56.json' -o 'AVM Email Contracts/generated_contract_files/staking_pool_manager_client.py'
algokitgen-py -a 'AVM Email Contracts/generated_contract_files/StakingPool.arc56.json' -o 'AVM Email Contracts/generated_contract_files/staking_pool_client.py'
```

**PowerShell**
```
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\EmailRegistry.arc56.json' -o 'AVM Email Contracts\generated_contract_files\registry_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\ServerContract.arc56.json' -o 'AVM Email Contracts\generated_contract_files\server_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\EmailContract.arc56.json' -o 'AVM Email Contracts\generated_contract_files\email_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\SpamEmail.arc56.json' -o 'AVM Email Contracts\generated_contract_files\spam_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\EmailListings.arc56.json' -o 'AVM Email Contracts\generated_contract_files\marketplace_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\PrivateStakingPoolManager.arc56.json' -o 'AVM Email Contracts\generated_contract_files\staking_pool_manager_client.py'
algokitgen-py -a 'AVM Email Contracts\generated_contract_files\StakingPool.arc56.json' -o 'AVM Email Contracts\generated_contract_files\staking_pool_client.py'
```

### Gainify

**TEAL, Mapping & ARC56 Json**

**Linux**
```
algokit compile py 'Gainify Contracts/master.py' --output-arc56 --out-dir generated_contract_files
algokit compile py 'Gainify Contracts/staking_pool.py' --output-arc56 --out-dir generated_contract_files
```

**PowerShell**
```
algokit compile py 'Gainify Contracts\master.py' --output-arc56 --out-dir generated_contract_files
algokit compile py 'Gainify Contracts\staking_pool.py' --output-arc56 --out-dir generated_contract_files
```

**Clients**

**Linux**
```
algokitgen-py -a 'Gainify Contracts/generated_contract_files/GainifyMasterApp.arc56.json' -o 'Gainify Contracts/generated_contract_files/master_client.py'
algokitgen-py -a 'Gainify Contracts/generated_contract_files/GainifyStakingPool.arc56.json' -o 'Gainify Contracts/generated_contract_files/pool_client.py'
```

**PowerShell**
```
algokitgen-py -a 'Gainify Contracts\generated_contract_files\GainifyMasterApp.arc56.json' -o 'Gainify Contracts\generated_contract_files\master_client.py'
algokitgen-py -a 'Gainify Contracts\generated_contract_files\GainifyStakingPool.arc56.json' -o 'Gainify Contracts\generated_contract_files\pool_client.py'
```

## Aggregated Compile Command for Testing

### Linux:

```
algokit compile py "Algofun Shares System Contract/shares_system_contract.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "AVM Email Contracts/avm_email_contracts.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "Gainify Contracts/master.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "Gainify Contracts/staking_pool.py" --output-arc56 --out-dir generated_contract_files;
algokitgen-py -a "Algofun Shares System Contract/generated_contract_files/AlgofunSharesSystem.arc56.json" -o "Algofun Shares System Contract/generated_contract_files/shares_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/EmailRegistry.arc56.json" -o "AVM Email Contracts/generated_contract_files/registry_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/ServerContract.arc56.json" -o "AVM Email Contracts/generated_contract_files/server_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/EmailContract.arc56.json" -o "AVM Email Contracts/generated_contract_files/email_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/SpamEmail.arc56.json" -o "AVM Email Contracts/generated_contract_files/spam_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/EmailListings.arc56.json" -o "AVM Email Contracts/generated_contract_files/marketplace_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/PrivateStakingPoolManager.arc56.json" -o "AVM Email Contracts/generated_contract_files/staking_pool_manager_client.py";
algokitgen-py -a "AVM Email Contracts/generated_contract_files/StakingPool.arc56.json" -o "AVM Email Contracts/generated_contract_files/staking_pool_client.py";
algokitgen-py -a "Gainify Contracts/generated_contract_files/GainifyMasterApp.arc56.json" -o "Gainify Contracts/generated_contract_files/master_client.py";
algokitgen-py -a "Gainify Contracts/generated_contract_files/GainifyStakingPool.arc56.json" -o "Gainify Contracts/generated_contract_files/pool_client.py"
```

### Powershell:

```
algokit compile py "Algofun Shares System Contract\shares_system_contract.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "AVM Email Contracts\avm_email_contracts.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "Gainify Contracts\master.py" --output-arc56 --out-dir generated_contract_files;
algokit compile py "Gainify Contracts\staking_pool.py" --output-arc56 --out-dir generated_contract_files;
algokitgen-py -a "Algofun Shares System Contract\generated_contract_files\AlgofunSharesSystem.arc56.json" -o "Algofun Shares System Contract\generated_contract_files\shares_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\EmailRegistry.arc56.json" -o "AVM Email Contracts\generated_contract_files\registry_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\ServerContract.arc56.json" -o "AVM Email Contracts\generated_contract_files\server_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\EmailContract.arc56.json" -o "AVM Email Contracts\generated_contract_files\email_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\SpamEmail.arc56.json" -o "AVM Email Contracts\generated_contract_files\spam_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\EmailListings.arc56.json" -o "AVM Email Contracts\generated_contract_files\marketplace_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\PrivateStakingPoolManager.arc56.json" -o "AVM Email Contracts\generated_contract_files\staking_pool_manager_client.py";
algokitgen-py -a "AVM Email Contracts\generated_contract_files\StakingPool.arc56.json" -o "AVM Email Contracts\generated_contract_files\staking_pool_client.py";
algokitgen-py -a "Gainify Contracts\generated_contract_files\GainifyMasterApp.arc56.json" -o "Gainify Contracts\generated_contract_files\master_client.py";
algokitgen-py -a "Gainify Contracts\generated_contract_files\GainifyStakingPool.arc56.json" -o "Gainify Contracts\generated_contract_files\pool_client.py"
```