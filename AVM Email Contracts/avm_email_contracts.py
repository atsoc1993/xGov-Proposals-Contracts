from algopy import arc4, subroutine, ARC4Contract, Account, Application, Txn, BoxMap, gtxn, itxn, Global, UInt64, urange, Bytes, ensure_budget, OpUpFeeSource, op, Asset, OnCompleteAction, TransactionType, BigUInt
from algopy.arc4 import abimethod, abi_call, Struct, Address, DynamicArray, String, DynamicBytes, arc4_signature



'''Email Info Per Account Address'''
class EmailInfoAccount(Struct):
    emails: DynamicArray[String]
    servers: DynamicArray[String]
    curve_accounts: DynamicArray[Address]
    child_email_apps: DynamicArray[arc4.UInt64]
    spam_email_apps: DynamicArray[arc4.UInt64]
    salts: DynamicArray[DynamicBytes]


'''Email Info per Email'''
class EmailInfo(Struct):
    account: Address
    curve_account: Address
    child_email_app: arc4.UInt64
    spam_email_app: arc4.UInt64
    salt: DynamicBytes
    allow_list: DynamicArray[DynamicBytes]

'''Server Box Value Info for Registry'''
class ServerBoxValue(Struct):
    owner: Address
    server_app: arc4.UInt64

'''Assembled Server Details returned from Registry, Obtained by Server Contract instance'''
class ServerDetails(Struct):
    server_owner: Address
    server_app: arc4.UInt64
    emails_unlocked: arc4.Bool
    base_character_cost: arc4.UInt64
    lp_buyback_burn_toggled: arc4.Bool
    buyback_and_burn_asset: arc4.UInt64

@subroutine
def is_creator() -> None:
    '''Sender is creator'''
    assert Txn.sender == Global.current_application_id.creator

@subroutine
def get_mbr() -> UInt64:
    '''Get current contract address' MBR'''
    return Global.current_application_address.min_balance
    
@subroutine
def refund_excess_mbr(excess: UInt64) -> None:
    '''Send an MBR payment with some excess amount calculated'''
    itxn.Payment(
        receiver=Txn.sender,
        amount=excess
    ).submit()

@subroutine
def contract_is_payment_receiver(txn: gtxn.PaymentTransaction) -> None:
    '''Check that receiver of some payment is this contract address'''
    assert txn.receiver == Global.current_application_address

'''Email Registry Contract 1 / 7 Contracts'''
class EmailRegistry(ARC4Contract):
    def __init__(self) -> None:
        self.email_accounts = BoxMap(Address, EmailInfoAccount, key_prefix='')
        self.emails = BoxMap(String, EmailInfo, key_prefix='')
        self.servers = BoxMap(String, ServerBoxValue, key_prefix='')
        self.server_app_template = Application()
        self.email_app_template = Application()
        self.spam_email_app_template = Application()
        self.email_listings_app = Application()
        self.algofun_shares_app = Application()
        # self.BONFIRE_APP = Application(497806551) #testnet
        self.BONFIRE_APP = Application(1257620981) #mainnet
        self.private_staking_pool_manager = Application(0)
    
    @abimethod
    def set_email_app_templates_and_other_apps(
        self, 
        server_app_template: Application, 
        email_app_template: Application, 
        spam_email_app_template: Application,
        email_listings_app: Application,
        private_staking_pool_manager: Application,
        algofun_shares_app: Application
        ) -> None:
        '''Set Global App Templates'''
        is_creator()
        self.server_app_template = server_app_template
        self.email_app_template = email_app_template
        self.spam_email_app_template = spam_email_app_template
        self.email_listings_app = email_listings_app
        self.private_staking_pool_manager = private_staking_pool_manager
        self.algofun_shares_app = algofun_shares_app

    @abimethod(allow_actions=['UpdateApplication'])
    def update_registry_contract(self) -> None:
        '''Update this registry if creator'''
        is_creator()
        
    @abimethod
    def create_server(
        self, 
        server: String, 
        emails_unlocked: bool,
        base_character_cost: UInt64,
        lp_buyback_burn_toggled: bool,
        asset: UInt64,
        pool_address: Address,
        bonfire_optin_payment: gtxn.PaymentTransaction,
        server_payment: gtxn.PaymentTransaction, 
        account_mbr_payment: gtxn.PaymentTransaction,
        mbr_payment: gtxn.PaymentTransaction
        ) -> None:
        '''Create a Server'''
        contract_is_payment_receiver(bonfire_optin_payment)
        contract_is_payment_receiver(txn=server_payment)
        contract_is_payment_receiver(txn=account_mbr_payment)
        contract_is_payment_receiver(txn=mbr_payment)

        assert server not in self.servers, "Server already exists"
        ALLOWED_CHARACTERS = Bytes(b"abcdefghijklmnopqrstuvwxyz1234567890")

        assert base_character_cost >= 1_000_000, "Character cost below minimum" #CHANGE THIS TO 1_000_000 (1 Algo)

        server_length = server.bytes.length - 2 # minus cursor bytes
        ensure_budget(700 * server_length * 2, OpUpFeeSource.GroupCredit)

        for i in urange(2, server.bytes.length):
            assert server.bytes[i] in ALLOWED_CHARACTERS, "Some characters not in allowed characters"

        assert server_length > 0, "Server length not greater than 0"
        assert server_length <= 25, "Server length greater than 25 characters"

        server_cost = UInt64(0)
        # Only use below in testnet
        # if server_length <= 6:
        #     match server_length:
        #         case UInt64(1):
        #             server_cost = UInt64(10_000)

        #         case UInt64(2):
        #             server_cost = UInt64(5_000)

        #         case UInt64(3):
        #             server_cost = UInt64(2_500)

        #         case UInt64(4):
        #             server_cost = UInt64(1_250)

        #         case UInt64(5):
        #             server_cost = UInt64(800)
                
        #         case UInt64(6):
        #             server_cost = UInt64(500)
                
        #         case _:
        #             server_cost = UInt64(100_000)
            
        # else:
        #     server_cost = UInt64(350)

        # TODO Add below back in for prod
        if server_length <= 6:
            match server_length:
                case UInt64(1):
                    server_cost = UInt64(10_000_000_000)

                case UInt64(2):
                    server_cost = UInt64(5_000_000_000)

                case UInt64(3):
                    server_cost = UInt64(2_500_000_000)

                case UInt64(4):
                    server_cost = UInt64(1_250_000_000)

                case UInt64(5):
                    server_cost = UInt64(800_000_000)
                
                case UInt64(6):
                    server_cost = UInt64(500_000_000)
                
                case _:
                    server_cost = UInt64(100_000_000_000)
            
        else:
            server_cost = UInt64(350_000_000)

        assert server_payment.amount == server_cost, "Server payment amount not equal to calculated cost"


        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=server_payment.amount
        )

        # the method being called in Shares System
        # def add_fees(self, fee_deposit: gtxn.PaymentTransaction) -> None:

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )


        pre_mbr = get_mbr()

        create_server_contract = itxn.ApplicationCall(
            approval_program=self.server_app_template.approval_program,
            clear_state_program=self.server_app_template.clear_state_program,
            global_num_bytes=32,
            global_num_uint=32,
            extra_program_pages=3
        ).submit()

        if lp_buyback_burn_toggled:
            assert account_mbr_payment.amount == 300_000, "Need Account MBR Payment of 300,000 Microalgo for Account + 2 Assets MBR Payment"
            itxn.Payment(
                receiver=create_server_contract.created_app.address,
                amount=300_000
            ).submit()
        else:
            assert account_mbr_payment.amount == 100_000, "Need Account MBR payment only of 100_000, not 300_000 without bonfire"
            itxn.Payment(
                receiver=create_server_contract.created_app.address,
                amount=100_000
            ).submit()

        owner = Address(Txn.sender)

        inner_bonfire_payment = itxn.Payment(
            receiver=create_server_contract.created_app.address,
            amount=bonfire_optin_payment.amount
        )

        abi_call(
            ServerContract.set_globals,
            self.email_listings_app,
            server,
            owner,
            emails_unlocked,
            base_character_cost,
            Global.current_application_id,
            arc4.Bool(lp_buyback_burn_toggled),
            asset,
            pool_address,
            inner_bonfire_payment,
            app_id=create_server_contract.created_app
        )
    
        self.servers[server] = ServerBoxValue(
            owner=Address(Txn.sender),
            server_app=arc4.UInt64(create_server_contract.created_app.id)
        )

        if owner in self.email_accounts:
            email_account = self.email_accounts[owner].copy()
            email_account.servers.append(server)
            self.email_accounts[owner] = email_account.copy()
        else:
            self.email_accounts[owner] = EmailInfoAccount(
                emails=DynamicArray[String](),
                servers=DynamicArray[String](server),
                curve_accounts=DynamicArray[Address](),
                child_email_apps=DynamicArray[arc4.UInt64](),
                spam_email_apps=DynamicArray[arc4.UInt64](),
                salts=DynamicArray[DynamicBytes](),
            )

        post_mbr = get_mbr()

        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess=excess_mbr)
        

    @abimethod
    def create_email(
        self, 
        full_email: String, 
        email: String, 
        server: String, 
        det_account: Address, 
        curve_account: Address, 
        salt: DynamicBytes, 
        email_payment: gtxn.PaymentTransaction, 
        mbr_payment: gtxn.PaymentTransaction
        ) -> None:
        '''Create an email under a server'''

        pre_mbr = get_mbr()
        ALLOWED_CHARACTERS = Bytes(b"abcdefghijklmnopqrstuvwxyz1234567890")
        assert full_email.bytes[-4:] == b'.avm', "Last 4 bytes are '.avm"
        at_symbol_index = full_email.bytes.length - server.bytes.length - 3
        assert full_email.bytes[at_symbol_index] == b'@', "@ symbol not at intended index of full email"
        server_index_start = at_symbol_index + 1
        assert full_email.bytes[server_index_start:-4] == server.bytes[2:], "Server bytes on full_email arg dont match server bytes in server arg"
        assert full_email.bytes.length > 6, "Must have 1 character for email, 1 @ symbol, 1 server character, and .avm,"
        assert salt.length > 0, "Salt not included"

        server_info = self.servers[server].copy()
        server_app = server_info.server_app.native
        server_owner = server_info.owner.native

        server_details, txn = abi_call(
            ServerContract.get_server_details,
            app_id=server_app
        )

        if Txn.sender != server_details.server_owner:
            assert server_details.emails_unlocked == True, "Emails are not unlocked for this server"
            assert email != 'admin'
        base_character_cost = server_details.base_character_cost.native
        buyback_and_burn_toggled = server_details.lp_buyback_burn_toggled

        full_email_length = (full_email.bytes.length - 7) - (server.bytes.length - 2) 
        ensure_budget(700 * full_email_length * 2, OpUpFeeSource.GroupCredit)

        for i in urange(2, at_symbol_index):
            assert full_email.bytes[i] in ALLOWED_CHARACTERS, "Some characters not in allowed characters"

        for i in urange(at_symbol_index + 1, full_email.bytes.length - 4):
            assert full_email.bytes[i] in ALLOWED_CHARACTERS, "Some characters not in allowed characters"


        assert full_email_length > 0, "full_email length not greater than 0"
        assert full_email_length <= 25, "full_email length greater than 25 characters"

        email_cost = base_character_cost * (26 - (email.bytes.length - 2))

        assert email_payment.amount == email_cost, "full_email payment does not match full_email cost"

        contract_is_payment_receiver(txn=mbr_payment)
        contract_is_payment_receiver(txn=email_payment)

        commission_amount = email_payment.amount // 2
        fee_amount = email_payment.amount - commission_amount

        # def add_fees(self, fee_deposit: gtxn.PaymentTransaction) -> None:

        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=fee_amount
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )



        server_app_address = Application(server_app).address
        if buyback_and_burn_toggled:
            commission_payment = itxn.Payment(
                receiver=server_app_address,
                amount=commission_amount,
            )
            

            txn = abi_call(
                ServerContract.buyback,
                commission_payment,
                app_id=server_app
            )

        else:
            itxn.Payment(
                amount=commission_amount,
                receiver=server_owner
            ).submit()

        owner = Address(Txn.sender)


        create_spam_email_account_tx = itxn.ApplicationCall(
            approval_program=self.spam_email_app_template.approval_program,
            clear_state_program=self.spam_email_app_template.clear_state_program,
            global_num_bytes=32,
            global_num_uint=32,
            extra_program_pages=3
        ).submit()

        itxn.Payment(
            receiver=create_spam_email_account_tx.created_app.address,
            amount=100_000
        ).submit()

        abi_call(
            SpamEmail.set_globals,
            owner,
            full_email,
            det_account,
            curve_account,
            salt,
            Global.current_application_id,
            self.algofun_shares_app,
            app_id=create_spam_email_account_tx.created_app
        )

        create_email_account_tx = itxn.ApplicationCall(
            approval_program=self.email_app_template.approval_program,
            clear_state_program=self.email_app_template.clear_state_program,
            global_num_bytes=32,
            global_num_uint=32,
            extra_program_pages=3
        ).submit()

        itxn.Payment(
            receiver=create_email_account_tx.created_app.address,
            amount=100_000
        ).submit()

        abi_call(
            EmailContract.set_globals,
            owner,
            full_email,
            det_account,
            curve_account,
            salt,
            Global.current_application_id,
            create_spam_email_account_tx.created_app,
            self.email_listings_app,
            app_id=create_email_account_tx.created_app
        )


        self.full_email_not_used(full_email=full_email)
        if owner in self.email_accounts:
            email_account = self.email_accounts[owner].copy()
            email_account.emails.append(full_email)
            email_account.curve_accounts.append(curve_account)
            email_account.child_email_apps.append(arc4.UInt64(create_email_account_tx.created_app.id))
            email_account.spam_email_apps.append(arc4.UInt64(create_spam_email_account_tx.created_app.id))
            email_account.salts.append(salt.copy())
            self.email_accounts[owner] = email_account.copy()
        else:
            self.email_accounts[owner] = EmailInfoAccount(
                emails=DynamicArray(full_email),
                servers=DynamicArray[String](),
                curve_accounts=DynamicArray(curve_account),
                child_email_apps=DynamicArray(arc4.UInt64(create_email_account_tx.created_app.id)),
                spam_email_apps=DynamicArray(arc4.UInt64(create_spam_email_account_tx.created_app.id)),
                salts=DynamicArray(salt.copy()),
            )



        self.emails[full_email] = EmailInfo(
            account=owner,
            curve_account=curve_account,
            child_email_app=arc4.UInt64(create_email_account_tx.created_app.id),
            spam_email_app=arc4.UInt64(create_spam_email_account_tx.created_app.id),
            salt=salt.copy(),
            allow_list=DynamicArray(DynamicBytes()),
        )
        post_mbr = get_mbr() + 200_000 # Add 200_000 for account MBR sent to email & spam email contracts

        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess=excess_mbr)


        result = abi_call(
            EmailContract.receive_email,
            Bytes(b'Welcome to avm.email!'),
            Global.current_application_id,
            note = (
                b"Welcome to avm.email!\n\n"
                b"You may be wondering, what now?\n\n"
                b"avm.email aims to be the encrypted communications channel of choice, "
                b"offering private, secure messaging and DeFi event coordination.\n"
                b"Today, you can message any email owner fully encrypted and list your email "
                b"email or entire server on our marketplace.\n\n"
                b'Server creators earn 50 percent commission on all initial email purchases under their server-'
                b" or forward revenue to "
                b"buyback, and add/burn liquidity tokens.\n\n"
                b"Coming soon: \nGroup Chats, enabling real-time encrypted communication for multiple users.\n"
                b"PSPs (Private Staking Pools), where server owners can:\n"
                b"A. Restrict pools to their server users\n"
                b"B. Allow access only to whitelisted users\n"
                b"C. Open access to all email owners\n\n"
            ),
            app_id=create_email_account_tx.created_app
        )
        

    @subroutine
    def full_email_not_used(self, full_email: String) -> None:
        '''Check this full email (email & server) not in use'''
        assert full_email not in self.emails

    @abimethod
    def server_exists(self, server: String) -> bool:
        '''Check server exists'''
        if server in self.servers:
            return True
        return False
    
    @abimethod
    def email_exists(self, full_email: String) -> bool:
        '''Check if an email exists'''
        if full_email in self.emails:
            return True
        return False

    @abimethod
    def get_email_info_by_account(self, owner: Address) -> EmailInfoAccount:
        '''Get email info by account address'''
        assert owner in self.email_accounts
        return self.email_accounts[owner]

    @abimethod
    def add_to_allow_list(self, email: String, new_allow_address: Address, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''Add someone to user's allow list for emails'''
        contract_is_payment_receiver(mbr_payment)
        pre_mbr = get_mbr()
        box_value = self.emails[email].copy()
        assert Txn.sender == box_value.account
        allow_list = box_value.allow_list.copy()
        present_in_allow_list = False
        for i in urange(allow_list.length):
            if allow_list[i].bytes[2:] == new_allow_address.bytes[:10]:
                present_in_allow_list = True
        assert present_in_allow_list == False
        box_value.allow_list.append(DynamicBytes(new_allow_address.bytes[:10]))
        self.emails[email] = box_value.copy()
        post_mbr = get_mbr()
        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess=excess_mbr)

    @abimethod
    def sender_in_allow_list(self, sender: Account, email: String) -> bool:
        '''Check if sender is in user's allow list'''
        box_value = self.emails[email].copy()
        present_in_allow_list = False
        for i in urange(box_value.allow_list.length):
            if box_value.allow_list[i].bytes[2:] == sender.bytes[:10]:
                present_in_allow_list = True
        return present_in_allow_list



    @abimethod
    def get_email_info_by_email(self, email: String) -> EmailInfo:
        '''Get email info by email'''
        return self.emails[email]

    @abimethod
    def get_server_info_by_email(self, server: String) -> ServerDetails:
        '''Get server info by email'''
        server_app_id = self.servers[server].copy().server_app.native
        result, txn = abi_call(
            ServerContract.get_server_details,
            app_id=server_app_id
        )
        return result
    
    
    @abimethod    
    def get_all_account_email_app_ids_and_encryption_accounts(
        self,
        account: Address
    ) -> EmailInfoAccount:
        '''Get all users encryption accounts and email app ids'''
        return self.email_accounts[account]
    
    @abimethod
    def transfer_server_ownership_internal_call(self, server: String, new_owner: Address) -> None:
        '''Transfer server ownership via sale'''
        server_details = self.servers[server].copy()
        assert Txn.sender == self.email_listings_app.address or Txn.sender == Application(self.servers[server].server_app.native).address
        previous_owner = server_details.owner
        prev_owner_account_info = self.email_accounts[previous_owner].copy()

        new_server_list = DynamicArray[String]()

        for i in urange(prev_owner_account_info.servers.length):
            if prev_owner_account_info.servers[i] != server:
                new_server_list.append(prev_owner_account_info.servers[i])

        prev_owner_account_info.servers = new_server_list.copy()
        self.email_accounts[previous_owner] = prev_owner_account_info.copy()

        server_details.owner = new_owner
        self.servers[server] = server_details.copy()


        new_owner_account_info = self.email_accounts[new_owner].copy()
        new_owner_account_info.servers.append(server)
        self.email_accounts[new_owner] = new_owner_account_info.copy()

    @abimethod
    def transfer_email_ownership_internal_call(self, full_email: String, new_owner: Address, new_det_account: Address, new_curve_account: Address, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''Transfer email ownership via sale'''
        contract_is_payment_receiver(txn=mbr_payment)

        email_info = self.emails[full_email].copy()

        assert Txn.sender == Application(email_info.child_email_app.native).address or Txn.sender == self.email_listings_app.address

        previous_owner = email_info.account

        email_info.allow_list = DynamicArray(DynamicBytes())
        email_info.account = new_owner
        self.emails[full_email] = email_info.copy()

        account_info = self.email_accounts[previous_owner].copy()

        new_prev_owner_account_info = EmailInfoAccount(
            emails=DynamicArray[String](),
            child_email_apps=DynamicArray[arc4.UInt64](),
            curve_accounts=DynamicArray[Address](),
            salts=DynamicArray[DynamicBytes](),
            spam_email_apps=DynamicArray[arc4.UInt64](),
            servers=DynamicArray[String]()
        )
        new_owner_info = self.email_accounts[new_owner].copy()
        
        for i in urange(account_info.child_email_apps.length):
            if account_info.emails[i] != full_email:
                new_prev_owner_account_info.emails.append(account_info.emails[i])
                new_prev_owner_account_info.curve_accounts.append(account_info.curve_accounts[i])
                new_prev_owner_account_info.child_email_apps.append(account_info.child_email_apps[i])
                new_prev_owner_account_info.salts.append(account_info.salts[i].copy())
                new_prev_owner_account_info.spam_email_apps.append(account_info.spam_email_apps[i])

            else:
                new_owner_info.emails.append(account_info.emails[i])
                new_owner_info.curve_accounts.append(new_curve_account)
                new_owner_info.child_email_apps.append(account_info.child_email_apps[i])
                new_owner_info.salts.append(account_info.salts[i].copy())
                new_owner_info.spam_email_apps.append(account_info.spam_email_apps[i])

        
        new_prev_owner_account_info.servers = account_info.servers.copy()
        pre_mbr = get_mbr()
        self.email_accounts[previous_owner] = new_prev_owner_account_info.copy()
        self.email_accounts[new_owner] = new_owner_info.copy()
        
        txn = abi_call(
            SpamEmail.transfer_ownership,
            new_owner,
            new_det_account,
            new_curve_account,
            app_id=email_info.spam_email_app.native
        )
        
        post_mbr = get_mbr()
        if post_mbr > pre_mbr:
            mbr_diff = post_mbr - pre_mbr
            itxn.Payment(
                amount=mbr_payment.amount - mbr_diff,
                receiver=new_owner.native
            ).submit()
        else:
            itxn.Payment(
                amount=mbr_payment.amount,
                receiver=new_owner.native
            ).submit()
            
    @subroutine
    def is_creating_pool(self) -> None:
        '''Ensure a pool is being created in this group transaction'''
        assert gtxn.ApplicationCallTransaction(5).app_args(0) == arc4_signature('create_staking_pool(string,uint64,uint64,txn,txn,txn)void'), "User not creating pool, cannot opt into assets"


    @abimethod
    def opt_into_assets(self, asset_to_stake: UInt64, reward_asset: UInt64, mbr_payment: gtxn.Transaction) -> None:
        '''Opt into a stakable asset and reward asset'''
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)
        self.is_creating_pool()

        pre_mbr = get_mbr()

        if asset_to_stake != 0:
            itxn.AssetTransfer(
                xfer_asset=asset_to_stake,
                asset_receiver=Global.current_application_address
            ).submit()

        if reward_asset != 0 and reward_asset != asset_to_stake:
            itxn.AssetTransfer(
                xfer_asset=reward_asset,
                asset_receiver=Global.current_application_address
            ).submit()

        post_mbr = get_mbr()
        mbr_cost = post_mbr - pre_mbr
        excess = mbr_payment.amount - mbr_cost
        refund_excess_mbr(excess)

    @abimethod
    def create_staking_pool(
        self,
        server: String,
        asset_to_stake: UInt64,
        pool_length: UInt64,
        reward_asset_deposit: gtxn.Transaction,
        platform_pool_creation_fee: gtxn.Transaction,
        mbr_payment: gtxn.Transaction
    ) -> None:
        '''Create a staking pool'''
        contract_is_receiver(reward_asset_deposit)
        contract_is_receiver(mbr_payment)
        contract_is_receiver(platform_pool_creation_fee)

        assert server in self.servers

        if reward_asset_deposit.type == TransactionType.Payment:
            forward_reward_asset_deposit = itxn.InnerTransaction(
                receiver=self.private_staking_pool_manager.address,
                amount=reward_asset_deposit.amount,
                type=TransactionType.Payment
            )

            reward_asset_id = reward_asset_deposit.xfer_asset.id
        
        else:
            forward_reward_asset_deposit = itxn.InnerTransaction(
                asset_receiver=self.private_staking_pool_manager.address,
                asset_amount=reward_asset_deposit.asset_amount,
                xfer_asset=reward_asset_deposit.xfer_asset,
                type=TransactionType.AssetTransfer

            )
            reward_asset_id = UInt64(0)

        is_payment_txn(platform_pool_creation_fee)
        is_payment_txn(mbr_payment)

        inner_mbr_txn = itxn.Payment(
            receiver=self.private_staking_pool_manager.address,
            amount=Global.asset_opt_in_min_balance * 2
        )

        txn = abi_call(
            PrivateStakingPoolManager.opt_into_assets,
            asset_to_stake,
            reward_asset_id,
            inner_mbr_txn,
            app_id=self.private_staking_pool_manager
        )

        forward_platform_pool_creation_fee = itxn.Payment(
            receiver=self.private_staking_pool_manager.address,
            amount=platform_pool_creation_fee.amount
        )

        forward_mbr_payment = itxn.Payment(
            receiver=self.private_staking_pool_manager.address,
            amount=mbr_payment.amount
        )
        
        txn = abi_call(
            PrivateStakingPoolManager.create_pool,
            Txn.sender,
            server,
            asset_to_stake,
            pool_length,
            forward_reward_asset_deposit,
            forward_platform_pool_creation_fee,
            forward_mbr_payment,
            app_id=self.private_staking_pool_manager
        )


        if reward_asset_deposit.type == TransactionType.AssetTransfer:
            itxn.AssetTransfer(
                xfer_asset=reward_asset_deposit.xfer_asset,
                asset_receiver=reward_asset_deposit.xfer_asset.creator,
                asset_close_to=reward_asset_deposit.xfer_asset.creator
            ).submit()
            
        post_balance = Global.current_application_address.balance

        excess = post_balance - get_mbr()
        refund_excess_mbr(excess)
        
    @abimethod
    def arbitrary_app_call(self) -> None:
        '''Arbitrary app call for additional box references (this method is outdated since new box updates)'''
        pass
    
    @abimethod
    def initialize_email_account(self, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''Initialize an email account in box storage'''
        contract_is_payment_receiver(mbr_payment)
        pre_mbr = get_mbr()
        assert Address(Txn.sender) not in self.email_accounts
        self.email_accounts[Address(Txn.sender)] = EmailInfoAccount(
            emails=DynamicArray[String](),
            servers=DynamicArray[String](),
            curve_accounts=DynamicArray[Address](),
            child_email_apps=DynamicArray[arc4.UInt64](),
            spam_email_apps=DynamicArray[arc4.UInt64](),
            salts=DynamicArray[DynamicBytes](),
        )
        post_mbr = get_mbr()
        excess_mbr = post_mbr - pre_mbr
        refund_excess_mbr(mbr_payment.amount - excess_mbr)

    @abimethod(allow_actions=['UpdateApplication'])
    def update_child(self, approval_program: Bytes, app_id: UInt64, email: String) -> None:
        '''Update an email, server, or spam child contract'''
        is_creator()
        clear_program = Bytes()
        if email == 'server':
            clear_program = self.server_app_template.clear_state_program
        elif email == 'email':
            clear_program = self.email_app_template.clear_state_program
        elif email == 'spam':
            clear_program = self.spam_email_app_template.clear_state_program

        itxn.ApplicationCall(
            approval_program=approval_program,
            clear_state_program=clear_program,
            on_completion=OnCompleteAction.UpdateApplication,
            app_id=app_id,
        ).submit()


'''Server Contract 2 / 7 Contracts'''
class ServerContract(ARC4Contract):
    def __init__(self) -> None:
        self.server = String()
        self.server_OWNER = Address()
        self.EMAILS_UNLOCKED = bool()
        self.EMAIL_COST_PER_CHARACTER = UInt64()
        self.EMAIL_REGISTRY = Application()
        self.EMAIL_LISTINGS_APP = Application()
        self.LP_BUYBACK_BURN_TOGGLED = bool()
        self.ASSET = UInt64()
        self.LP_ASSET = Asset()
        self.POOL_ADDRESS = Address()
        # self.BONFIRE_APP = Application(497806551) #testnet
        self.BONFIRE_APP = Application(1257620981) #mainnet
        # self.TINYMAN_ROUTER = Application(148607000) #testnet
        self.TINYMAN_ROUTER = Application(1002541853) #mainnet


    @abimethod(allow_actions=['UpdateApplication'])
    def update_server_contract(self) -> None:
        '''Update contract if creator'''
        is_creator()



    @abimethod
    def transfer_server_ownership(self, new_owner: Address) -> None:
        '''Transfer server ownership via internal method in registry'''
        assert Txn.sender == self.EMAIL_LISTINGS_APP.address or Txn.sender == self.server_OWNER
        self.server_OWNER = new_owner
        txn = abi_call(
            EmailRegistry.transfer_server_ownership_internal_call,
            self.server,
            new_owner,
            app_id=self.EMAIL_REGISTRY
        )


    @abimethod
    def set_globals(
        self, 
        email_listings_app: Application,
        server: String, 
        server_owner: Address, 
        emails_unlocked: bool, 
        base_character_cost: UInt64, 
        email_registry: Application, 
        lp_buyback_burn_toggled: bool, 
        asset: UInt64,
        pool_address: Address,
        bonfire_optin_payment: gtxn.PaymentTransaction,
    ) -> None:
        '''Set intial global parameters'''
        assert Txn.sender == Global.creator_address
        self.EMAIL_LISTINGS_APP = email_listings_app
        contract_is_payment_receiver(bonfire_optin_payment)

        if lp_buyback_burn_toggled:
            LP_asset, asset_a, asset_b = self.get_tiny_pool_info(pool_account=pool_address.native)

            itxn.AssetTransfer(
                xfer_asset=asset_a,
                asset_receiver=Global.current_application_address
            ).submit()

            itxn.AssetTransfer(
                xfer_asset=LP_asset,
                asset_receiver=Global.current_application_address
            ).submit()

            assert asset_a == asset
            assert asset_b == 0

            if not self.BONFIRE_APP.address.is_opted_in(LP_asset):
                assert bonfire_optin_payment.amount == 100_000, "Did not send bonfire optin fee"
                bonfire_mbr_needed = self.opt_bonfire_into_asset(asset=LP_asset)

            else:
                assert bonfire_optin_payment.amount == 0, "Does not require bonfire optin fee, set amount to 0"

        self.server_OWNER = server_owner
        self.server = server
        self.EMAILS_UNLOCKED = emails_unlocked
        self.EMAIL_REGISTRY = email_registry
        self.LP_BUYBACK_BURN_TOGGLED = lp_buyback_burn_toggled
        self.ASSET = asset
        self.LP_ASSET = LP_asset
        self.POOL_ADDRESS = pool_address
        self.EMAIL_COST_PER_CHARACTER = base_character_cost


    @abimethod
    def get_server_details(self) -> ServerDetails:
        '''Get server details'''
        return ServerDetails(
            server_owner=self.server_OWNER,
            server_app=arc4.UInt64(Global.current_application_id.id),
            base_character_cost=arc4.UInt64(self.EMAIL_COST_PER_CHARACTER),
            emails_unlocked=arc4.Bool(self.EMAILS_UNLOCKED),
            lp_buyback_burn_toggled=arc4.Bool(self.LP_BUYBACK_BURN_TOGGLED),
            buyback_and_burn_asset=arc4.UInt64(self.ASSET)
        )


    @abimethod
    def buyback(self, buyback_and_burn_lp_payment: gtxn.PaymentTransaction) -> None:
        '''Buyback and burn the token designated for this server with some algo amount'''
        asset = Asset(self.ASSET)
        contract_is_payment_receiver(buyback_and_burn_lp_payment)
        LP_token, asset_a_id, asset_b_id = self.get_tiny_pool_info(pool_account=self.POOL_ADDRESS.native)
        assert asset_a_id == asset.id and asset_b_id == 0, 'Asset A and Asset B ID\'s do not match Pool Local State INFO'

        asset_purchase_amount = buyback_and_burn_lp_payment.amount // 2
        remaining_lp_amount = buyback_and_burn_lp_payment.amount - asset_purchase_amount

        purchase_entry_asset = itxn.Payment(
            receiver=self.POOL_ADDRESS.native,
            amount=asset_purchase_amount,
        )

        arg_1 = Bytes(b'swap')
        arg_2 = Bytes(b'fixed-input')
        arg_3 = arc4.UInt64(0).bytes

        args = (arg_1, arg_2, arg_3)

        
        entry_asset_buy = itxn.ApplicationCall(
            app_id=self.TINYMAN_ROUTER,
            on_completion=OnCompleteAction.NoOp,
            app_args=args,
            accounts=(self.POOL_ADDRESS.native,),
            assets=(asset,)
        )

        tx_1, tx_2 = itxn.submit_txns(purchase_entry_asset, entry_asset_buy)

        transfer_algo = itxn.Payment(receiver=self.POOL_ADDRESS.native, amount=remaining_lp_amount)
        transfer_asset = itxn.AssetTransfer(xfer_asset=asset, asset_receiver=self.POOL_ADDRESS.native, asset_amount=asset.balance(Global.current_application_address))
        liq_arg_1 = Bytes(b'add_liquidity')
        liq_arg_2 = Bytes(b'flexible')
        liq_arg_3 = arc4.UInt64(0).bytes
        tiny_args = (liq_arg_1, liq_arg_2, liq_arg_3)
        add_lp_call = itxn.ApplicationCall(
            app_id=self.TINYMAN_ROUTER,
            on_completion=OnCompleteAction.NoOp,
            app_args=(tiny_args),
            assets=(LP_token,),
            accounts=(self.POOL_ADDRESS.native,)
        )
        itxn.submit_txns(transfer_asset, transfer_algo, add_lp_call)

        itxn.AssetTransfer(
            xfer_asset=LP_token,
            asset_amount=LP_token.balance(Global.current_application_address),
            asset_receiver=self.BONFIRE_APP.address
        ).submit()



    @subroutine
    def opt_bonfire_into_asset(self, asset: Asset) -> UInt64:
        '''Opt bonfire into some asset if not opted in'''
        if not self.BONFIRE_APP.address.is_opted_in(asset):
            optin_sig = arc4_signature('arc54_optIntoASA(asset)void')
            second_app_arg = arc4.UInt16(0).bytes
            app_args = (optin_sig, second_app_arg)


            mbr_txn = itxn.Payment(
                receiver=self.BONFIRE_APP.address,
                amount=100_000
            )
            optin_app_call = itxn.ApplicationCall(
                app_id=self.BONFIRE_APP, 
                on_completion=OnCompleteAction.NoOp, 
                app_args=app_args, 
                assets=(asset,)
            )
            mbr_txn_result, optin_txn_result = itxn.submit_txns(mbr_txn, optin_app_call)

            return UInt64(100_000)
        
        return UInt64(0)





    @abimethod
    def adjust_server_settings(
        self,
        emails_unlocked: bool,
        buyback_and_burn_toggled: bool,
        buyback_and_burn_asset: Asset,
        pool_address: Address,
        base_character_cost: UInt64,
        mbr_payment: gtxn.PaymentTransaction
    ) -> None:
        '''Configure this server's mutable settings'''
        assert Txn.sender == self.server_OWNER

        contract_is_payment_receiver(mbr_payment)

        pre_mbr = get_mbr()

        self.EMAILS_UNLOCKED = emails_unlocked
        self.EMAIL_COST_PER_CHARACTER = base_character_cost
        
        bonfire_mbr_needed = UInt64(0)
        if buyback_and_burn_toggled:
            assert buyback_and_burn_asset.id != 0
            self.LP_BUYBACK_BURN_TOGGLED = True
            bonfire_mbr_needed = self.switch_buyback_and_burn_asset(buyback_and_burn_asset, pool_address)

        else:
            self.LP_BUYBACK_BURN_TOGGLED = False
            self.LP_ASSET = Asset(0)
            self.ASSET = UInt64(0)
            
        post_mbr = get_mbr() + bonfire_mbr_needed

        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess_mbr)

    @subroutine
    def switch_buyback_and_burn_asset(self, asset: Asset, pool_address: Address) -> UInt64:
        '''Modify buyback and burn asset designated for this server'''
        self.ASSET = asset.id
        
        self.POOL_ADDRESS = pool_address
        LP_asset, asset_a, asset_b = self.get_tiny_pool_info(pool_account=pool_address.native)
        self.LP_ASSET = LP_asset

        bonfire_mbr_needed = UInt64(0)
        bonfire_mbr_needed += self.opt_bonfire_into_asset(Asset(asset_a))
        bonfire_mbr_needed += self.opt_bonfire_into_asset(LP_asset)

        if not Global.current_application_address.is_opted_in(asset):
            itxn.AssetTransfer(
                xfer_asset=asset_a,
                asset_receiver=Global.current_application_address
            ).submit()

        if not Global.current_application_address.is_opted_in(LP_asset):
            itxn.AssetTransfer(
                xfer_asset=LP_asset,
                asset_receiver=Global.current_application_address
            ).submit()

        return bonfire_mbr_needed


    @subroutine
    def get_tiny_pool_info(self, pool_account: Account) -> tuple[Asset, UInt64, UInt64]:
        '''Get information about a Tiny pool from a pool address'''
        LP_token = Asset(op.AppLocal.get_ex_uint64(pool_account, self.TINYMAN_ROUTER, b'pool_token_asset_id')[0])
        asset_a_id = op.AppLocal.get_ex_uint64(pool_account, self.TINYMAN_ROUTER, b'asset_1_id')[0]  
        asset_b_id = op.AppLocal.get_ex_uint64(pool_account, self.TINYMAN_ROUTER, b'asset_2_id')[0]
      
        return LP_token, asset_a_id, asset_b_id
    

'''Email Contract 3 / 7 Contracts'''
class EmailContract(ARC4Contract):
    def __init__(self) -> None:
        self.EMAIL_OWNER = Address()
        self.CURVE25519_ACCOUNT = Address()
        self.EMAIL_REGISTRY = Application()
        self.EMAIL_email = String()
        self.SPAM_APP_ID = Application()
        self.EMAIL_LISTINGS_APP = Application()
        self.SALT = Bytes()

    @abimethod(allow_actions=['UpdateApplication'])
    def update_email_contract(self) -> None:
        '''Update this Email Contract if creator'''
        is_creator()

    @abimethod
    def set_globals(
        self, 
        owner: Address, 
        email: String, 
        det_account: Address, 
        curve_account: Address, 
        salt: Bytes, 
        email_registry: Application, 
        spam_app_id: Application, 
        email_listings_app: Application
    ) -> None:
        '''Set Globals for this users email'''
        assert Txn.sender == email_registry.address
        self.EMAIL_OWNER = owner
        self.DETERMINISTIC_ACCOUNT = det_account
        self.CURVE25519_ACCOUNT = curve_account
        self.SALT = salt
        self.EMAIL_REGISTRY = email_registry
        self.EMAIL_email = email
        self.SPAM_APP_ID = spam_app_id
        self.EMAIL_LISTINGS_APP = email_listings_app

    @abimethod
    def send_email_by_email(self, email: String, subject: Bytes, det_account: Address) -> None:
        '''Send an email and use another email directly for the "to" field'''
        assert Txn.sender == self.EMAIL_OWNER, "Email owner not sender"
        assert det_account == self.DETERMINISTIC_ACCOUNT, "Det account mismatch"
        receiver_info, txn = abi_call(
            EmailRegistry.get_email_info_by_email,
            email,
            app_id=self.EMAIL_REGISTRY,
            note=Txn.note
        )

        in_allow_list, txn = abi_call(
            EmailRegistry.sender_in_allow_list,
            Txn.sender,
            email,
            app_id=self.EMAIL_REGISTRY
        )

        if in_allow_list:
            abi_call(
                'receive_email(byte[],uint64)void',
                subject,
                Global.current_application_id,
                app_id=receiver_info.child_email_app.native,
                note=Txn.note,
            )

        else:
            abi_call(
                'receive_email(byte[],uint64)void',
                subject,
                Global.current_application_id,
                app_id=receiver_info.spam_email_app.native,
                note=Txn.note,
            )

    @abimethod
    def transfer_email_ownership(self, new_owner: Address, new_det_account: Address, new_curve_account: Address, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''Transfer email ownership via internal method in registry'''
        contract_is_payment_receiver(txn=mbr_payment)

        assert Txn.sender == self.EMAIL_OWNER or Txn.sender == self.EMAIL_LISTINGS_APP.address
        self.EMAIL_OWNER = new_owner
        self.DETERMINISTIC_ACCOUNT = new_det_account
        self.CURVE25519_ACCOUNT = new_curve_account
        
        new_inner_mbr_payment = itxn.Payment(
            amount=mbr_payment.amount,
            receiver=self.EMAIL_REGISTRY.address
        )

        txn = abi_call(
            EmailRegistry.transfer_email_ownership_internal_call,
            self.EMAIL_email,
            new_owner,
            new_det_account,
            new_curve_account,
            new_inner_mbr_payment,
            app_id=self.EMAIL_REGISTRY
        )

    @abimethod
    def claim_ownership(self, new_det_account: Address, new_curve_account: Address) -> None:
        '''Claim Ownership of this email account if owner and set the deterministic & curve accounts'''
        assert Txn.sender == self.EMAIL_OWNER
        self.DETERMINISTIC_ACCOUNT = new_det_account
        self.CURVE25519_ACCOUNT = new_curve_account

    @abimethod
    def send_email_by_account(self, subject: Bytes, receiver: Address, det_account: Address) -> None:
        '''Send email and use the receiver address as the "to" field'''
        assert Txn.sender == self.EMAIL_OWNER
        assert det_account == self.DETERMINISTIC_ACCOUNT
        receiver_info, txn = abi_call(
            EmailRegistry.get_email_info_by_account,
            receiver,
            app_id=self.EMAIL_REGISTRY
        )

        in_allow_list, txn = abi_call(
            EmailRegistry.sender_in_allow_list,
            Txn.sender,
            receiver_info.emails[0],
            app_id=self.EMAIL_REGISTRY
        )

        if in_allow_list:
            abi_call(
                'receive_email(byte[],uint64)void',
                subject,
                Global.current_application_id,
                note=Txn.note,
                app_id=receiver_info.child_email_apps[0].native
            )

        else:
            abi_call(
                'receive_email(byte[],uint64)void',
                subject,
                Global.current_application_id,
                note=Txn.note,
                app_id=receiver_info.spam_email_apps[0].native
            )

    @abimethod
    def receive_email(self, subject: Bytes, calling_app: Application) -> None:
        '''Receive an email from some other user'''
        if calling_app != self.EMAIL_REGISTRY:
            assert calling_app.creator == Global.creator_address
            assert calling_app.address == Txn.sender
            sender_email = op.AppGlobal.get_ex_bytes(calling_app, b'EMAIL_email')[0]

        else:
            sender_email = Bytes(b'  avm.email')

        itxn.Payment(
            amount=0,
            receiver=self.EMAIL_OWNER.native,
            note=b'Received an email from ' + sender_email[2:] + b' to ' + self.EMAIL_email.bytes[2:]
        ).submit()


'''Spam Email Contract 4 / 7 Contracts'''
class SpamEmail(ARC4Contract):
    def __init__(self) -> None:
        self.EMAIL_OWNER = Address()
        self.CURVE25519_ACCOUNT = Address()
        self.EMAIL_REGISTRY = Application()
        self.EMAIL_email = String()
        self.SALT = Bytes()
        self.SPAM = True


    @abimethod(allow_actions=['UpdateApplication'])
    def update_spam_email_contract(self) -> None:
        '''Update contract if creator'''
        is_creator()

        
    @abimethod
    def set_globals(
        self, 
        owner: Address, 
        email: String, 
        det_account: Address, 
        curve_account: Address, 
        salt: Bytes, 
        email_registry: Application,
        algofun_shares_app: Application
    ) -> None:
        '''Set Globals for this Spam Email'''
        assert Txn.sender == email_registry.address
        self.EMAIL_OWNER = owner
        self.DETERMINISTIC_ACCOUNT = det_account
        self.CURVE25519_ACCOUNT = curve_account
        self.EMAIL_REGISTRY = email_registry
        self.EMAIL_email = email
        self.SALT = salt
        self.algofun_shares_app = algofun_shares_app

    @abimethod
    def transfer_ownership(self, new_owner: Address, new_det_account: Address, new_curve_account: Address) -> None:
        '''Called to transfer ownership when a sale has occured'''
        assert Txn.sender == self.EMAIL_REGISTRY.address
        self.EMAIL_OWNER = new_owner
        self.DETERMINISTIC_ACCOUNT = new_det_account
        self.CURVE25519_ACCOUNT = new_curve_account

    @abimethod
    def receive_email(self, subject: Bytes, calling_app: Application) -> None:
        '''Receive a spam email'''
        assert calling_app.creator == Global.creator_address
        assert calling_app.address == Txn.sender
        
        sender_email = op.AppGlobal.get_ex_bytes(calling_app.id, b'EMAIL_email')[0]

        itxn.Payment(
            amount=0,
            receiver=self.EMAIL_OWNER.native,
            note=b'Received a spam email from ' + sender_email[2:] + b' to ' + self.EMAIL_email.bytes[2:] + b'. Forwarded to Junk Mail, add this sender to your allow list if you know them!'
        ).submit()

class Listing(Struct):
    lister: Address
    algo_amount: arc4.UInt64

'''Email Marketplace Contract 5 / 7 Contracts'''
class EmailListings(ARC4Contract):
    def __init__(self) -> None:
        self.server_listings = BoxMap(String, Listing, key_prefix='server')
        self.email_listings = BoxMap(String, Listing, key_prefix='email')
        self.REGISTRY_APP = Application()
        self.algofun_shares_app = Application()
        self.fee = UInt64(5)

    @abimethod
    def set_globals(self, registry_app: Application, algofun_shares_app: Application) -> None:
        '''Set globals for the email registry and include Algofun Shares System Integration'''
        is_creator()
        self.REGISTRY_APP_ID = registry_app
        self.algofun_shares_app = algofun_shares_app

    @abimethod(allow_actions=['UpdateApplication'])
    def update_listings_contract(self) -> None:
        '''Update this marketplace contract if creator'''
        is_creator()

    @abimethod
    def create_server_listing(self, server: String, sell_amount_in_microalgo: arc4.UInt64, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''List a server for sale'''
        contract_is_payment_receiver(mbr_payment)
        server_info, txn = abi_call(
            EmailRegistry.get_server_info_by_email,
            server,
            app_id=self.REGISTRY_APP_ID
        )

        assert Txn.sender == server_info.server_owner
        
        pre_mbr = get_mbr()

        listing_info = Listing(
            lister=Address(Txn.sender),
            algo_amount=sell_amount_in_microalgo
        )
        self.server_listings[server] = listing_info.copy()

        post_mbr = get_mbr()
        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess=excess_mbr)

    @abimethod
    def purchase_server_listing(self, server: String, payment: gtxn.PaymentTransaction) -> None:
        '''Purchase a server that is for sale'''
        contract_is_payment_receiver(payment)

        algo_sent = payment.amount
        algo_requested = self.server_listings[server].algo_amount.native
        assert algo_sent == algo_requested
        fee_amount = (algo_requested * self.fee) // 100
        algo_after_fee = algo_requested - fee_amount

        server_info, txn = abi_call(
            EmailRegistry.get_server_info_by_email,
            server,
            app_id=self.REGISTRY_APP_ID
        )
        

        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=fee_amount
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )

        itxn.Payment(
            receiver=server_info.server_owner.native,
            amount=algo_after_fee,
            note='Someone purchased your AVM server: ' + server.native
        ).submit()

        txn = abi_call(
            ServerContract.transfer_server_ownership,
            Address(Txn.sender),
            app_id=server_info.server_app.native
        )

        del self.server_listings[server]

    @abimethod
    def create_email_listing(self, full_email: String, sell_amount_in_microalgo: arc4.UInt64, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''List an email for sale'''
        contract_is_payment_receiver(mbr_payment)
        email_info, txn = abi_call(
            EmailRegistry.get_email_info_by_email,
            full_email,
            app_id=self.REGISTRY_APP_ID
        )

        assert Txn.sender == email_info.account
        pre_mbr = get_mbr()

        listing_info = Listing(
            lister=Address(Txn.sender),
            algo_amount=sell_amount_in_microalgo
        )

        self.email_listings[full_email] = listing_info.copy()
        post_mbr = get_mbr()
        mbr_diff = post_mbr - pre_mbr
        excess_mbr = mbr_payment.amount - mbr_diff
        refund_excess_mbr(excess=excess_mbr)

    @abimethod
    def purchase_email_listing(
        self, 
        full_email: String, 
        new_det_account: Address, 
        new_curve_account: Address, 
        payment: gtxn.PaymentTransaction,
        mbr_payment: gtxn.PaymentTransaction
    ) -> None:
        '''Purchase an email listed for sale'''
        contract_is_payment_receiver(payment)
        contract_is_payment_receiver(mbr_payment)
        algo_sent = payment.amount
        algo_requested = self.email_listings[full_email].algo_amount.native

        assert algo_sent == algo_requested
        fee_amount = (algo_requested * 5) // 100
        algo_after_fee = algo_requested - fee_amount
        
        email_info, txn = abi_call(
            EmailRegistry.get_email_info_by_email,
            full_email,
            app_id=self.REGISTRY_APP_ID
        )


        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=fee_amount
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )
        

        itxn.Payment(
            receiver=email_info.account.native,
            amount=algo_after_fee,
            note='Someone purchased your AVM full_email: ' + full_email.native
        ).submit()

        new_inner_mbr_payment = itxn.Payment(
            receiver=Application(email_info.child_email_app.native).address,
            amount=mbr_payment.amount
        )

        txn = abi_call(
            EmailContract.transfer_email_ownership,
            Address(Txn.sender),
            new_det_account,
            new_curve_account,
            new_inner_mbr_payment,
            app_id=email_info.child_email_app.native
        )

        del self.email_listings[full_email]

    @abimethod
    def cancel_listing_of_any_type(self, server_or_fullemail: String, type: String) -> None:
        '''Cancel listing of any type (server / email)'''
        pre_mbr = get_mbr()

        if type == 'email':
            assert server_or_fullemail in self.email_listings
            email_info, txn = abi_call(
                EmailRegistry.get_email_info_by_email,
                server_or_fullemail,
                app_id=self.REGISTRY_APP_ID
            )
            assert Txn.sender == email_info.account
            del self.email_listings[server_or_fullemail]

        elif type == 'server':
            assert server_or_fullemail in self.server_listings
            server_info, txn = abi_call(
                EmailRegistry.get_server_info_by_email,
                server_or_fullemail,
                app_id=self.REGISTRY_APP_ID
            )
            assert Txn.sender == server_info.server_owner
            del self.server_listings[server_or_fullemail]

        post_mbr = get_mbr()
        
        mbr_diff = pre_mbr - post_mbr
        refund_excess_mbr(excess=mbr_diff)

    @abimethod
    def arbitrary_app_call(self) -> None:
        '''Arbitrary app call for additional box references (Box reference updates have rendered this method working but deprecated)'''
        pass
    


@subroutine
def contract_is_receiver(txn: gtxn.Transaction) -> None:
    '''Check the contract is the receiver of a payment or asset transfer'''
    if txn.type == TransactionType.Payment:
        assert txn.receiver == Global.current_application_address, "Contract is not receiver of payment txn"
    elif txn.type == TransactionType.AssetTransfer:
        assert txn.asset_receiver == Global.current_application_address, "Contract is not receiver of asset transfer"

@subroutine
def is_payment_txn(txn: gtxn.Transaction) -> None:
    '''Check if a transaction is a payment'''
    assert txn.type == TransactionType.Payment, "Not a payment txn"


'''Pool Box Name Reference'''
class PoolRefBoxName(Struct):
    server: String
    asset_to_stake: arc4.UInt64
    reward_asset: arc4.UInt64
    reward_total: arc4.UInt64
    pool_length: arc4.UInt64

'''Pool Box Reference Value'''
class PoolRefBoxValue(Struct):
    pool_app_id: arc4.UInt64

'''Staking Pool Manager Contract 6 / 7 Contracts'''
class PrivateStakingPoolManager(ARC4Contract):
    def __init__(self) -> None:
        self.pool_app_template = Application(0)
        self.pool_refs = BoxMap(PoolRefBoxName, PoolRefBoxValue, key_prefix='')
        self.min_reward_per_day = UInt64(10)
        self.min_pool_length = UInt64(604_800)
        # self.min_pool_length = UInt64(60)
        self.max_pool_length = UInt64(7_257_600)
        # self.tinyman_router = Application(148607000) #testnet
        self.tinyman_router = Application(1002541853) #mainnet

        self.pool_logicsig_template = op.base64_decode(op.Base64.StdEncoding, b"BoAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgQBbNQA0ADEYEkQxGYEBEkSBAUM=")
        # self.USDC = UInt64(10458941) # Testnet USDC
        self.USDC = UInt64(31566704) # Mainnet USDC
        self.REGISTRY_APP = Application(0)

        self.algofun_shares_app = Application()

    @abimethod(allow_actions=['UpdateApplication', 'DeleteApplication'])
    def update_or_delete(self) -> None:
        '''Update or delete application if creator'''
        is_creator()

    @abimethod
    def set_registry_app_shares_app_and_pool_app_template(
        self, 
        registry_app: Application, 
        pool_app_template: Application,
        algofun_shares_app: Application,
    ) -> None:
        '''Set global registry app and pool app templates'''
        is_creator()
        self.REGISTRY_APP = registry_app
        self.algofun_shares_app = algofun_shares_app
        self.pool_app_template = pool_app_template


    @abimethod
    def opt_into_assets(self, asset_to_stake: UInt64, reward_asset: UInt64, mbr_payment: gtxn.Transaction) -> None:
        '''Opt into assets'''
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)

        pre_mbr = get_mbr()

        if asset_to_stake != 0:
            itxn.AssetTransfer(
                xfer_asset=asset_to_stake,
                asset_receiver=Global.current_application_address
            ).submit()

        if reward_asset != 0 and reward_asset != asset_to_stake:
            itxn.AssetTransfer(
                xfer_asset=reward_asset,
                asset_receiver=Global.current_application_address
            ).submit()

        post_mbr = get_mbr()
        mbr_cost = post_mbr - pre_mbr
        excess = mbr_payment.amount - mbr_cost
        refund_excess_mbr(excess)



    @abimethod
    def create_pool(
        self,
        creator: Account,
        server: String,
        asset_to_stake: UInt64,
        pool_length: UInt64,
        reward_asset_deposit: gtxn.Transaction,
        platform_pool_creation_fee: gtxn.Transaction,
        mbr_payment: gtxn.Transaction,
    ) -> None:
        '''Create a pool'''
        assert Txn.sender == self.REGISTRY_APP.address
        contract_is_receiver(reward_asset_deposit)
        contract_is_receiver(mbr_payment)
        contract_is_receiver(platform_pool_creation_fee)
        is_payment_txn(mbr_payment)
        is_payment_txn(platform_pool_creation_fee)
        assert platform_pool_creation_fee.amount == 50_000_000
        self.forward_platform_fee(platform_pool_creation_fee.amount)
        self.validate_asset_to_stake(asset_to_stake)
        self.validate_pool_length(pool_length)
        reward_asset, reward_amount = self.valid_reward_to_pool_length_ratio(reward_asset_deposit, pool_length)
        self.deploy_and_initialize_pool(asset_to_stake, reward_asset, reward_amount, pool_length, mbr_payment, creator, server)

    @abimethod
    def delete_pool_box(self, calling_app_id: Application, pool_ref_box_email: Bytes) -> None:
        '''Delete a pool box'''
        assert calling_app_id.address == Txn.sender or Global.creator_address == Txn.sender
        pool_ref_box_email_struct = PoolRefBoxName.from_bytes(pool_ref_box_email)
        pool_app_id = self.pool_refs[pool_ref_box_email_struct].pool_app_id
        assert calling_app_id.id == pool_app_id
        pre_mbr = get_mbr()
        del self.pool_refs[pool_ref_box_email_struct]
        post_mbr = get_mbr()
        mbr_diff = pre_mbr - post_mbr
        itxn.Payment(
            receiver=Txn.sender,
            amount=mbr_diff,
            note='Last user unstaked and pool ended, deleted pool ref in PSP Manager'
        ).submit()

    @subroutine
    def forward_platform_fee(
        self,
        amount: UInt64
    ) -> None:
        '''Forward a platform fee to the algofun shares system'''

        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=amount
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )


    @subroutine
    def validate_asset_to_stake(self, asset_to_stake: UInt64) -> None:
        '''Check if ASA ID provided still exists (not destroyed) or is Algo'''
        assert asset_to_stake == 0 or Asset(asset_to_stake).name, "Asset is not Algo or valid ASA"

    @subroutine
    def validate_pool_length(self, pool_length: UInt64) -> None:
        '''Ensure pool is still live'''
        assert self.min_pool_length <= pool_length <= self.max_pool_length, "Pool length must be at least 7 days, and at most 3 months"
        
    @subroutine
    def valid_reward_to_pool_length_ratio(self, reward_asset_deposit: gtxn.Transaction, pool_length: UInt64) -> tuple[UInt64, UInt64]:
        '''Ensure the reward rate is logical'''
        reward_asset, reward_amount = self.get_reward_asset_and_deposit_amount(reward_asset_deposit)

        reward_asset_tiny_pool_logicsig_address = self.get_logicsig_address(reward_asset) # A pool must exist for the asset

        #Insert these lines back if we care about the total USD amount per day
        # usdc_tiny_pool_logic_sig_address = self.get_logicsig_address(self.USDC)
        # scaled_algo_price = self.get_scaled_price(usdc_tiny_pool_logic_sig_address)
        # scaled_asset_price = self.get_scaled_price(reward_asset_tiny_pool_logicsig_address)
        # assert ((scaled_asset_price * reward_amount * scaled_algo_price) // 1_000_000) // (((pool_length // 60) // 60) // 24)  > self.min_reward_per_day # At least $10 worth of total rewards per day in the pool

        #PUT THIS (BELOW) BACK OR REMOVE COMPLETELY, % FEE OF REWARD ASSET
        if reward_asset == 0:
            fee_amount = (reward_amount * 5) // 100
            reward_amount = reward_amount - fee_amount

        else:
            fee_amount = (reward_amount * 5) // 100
            reward_amount = reward_amount - fee_amount
            #PUT THIS (BELOW) BACK OR REMOVE COMPLETELY, % FEE OF REWARD ASSET, REMOVING DURING TESTING SO WE DONT HAVE TO CONSTANTLY BOOTSTRAP TOKENS FOR TESTING

            # fee_amount, reward_amount = self.sell_asset_portion(
            #     reward_asset=reward_asset, 
            #     reward_amount=reward_amount,
            #     reward_asset_tiny_pool_logicsig_address=reward_asset_tiny_pool_logicsig_address
            # )

        self.forward_platform_fee(amount=fee_amount) #KEEP OR REMOVE

        return reward_asset, reward_amount

    @subroutine
    def get_reward_asset_and_deposit_amount(self, reward_asset_deposit: gtxn.Transaction) -> tuple[UInt64, UInt64]:
        '''Get the deposit amount of the reward asset'''
        if reward_asset_deposit.type == TransactionType.Payment:
            return UInt64(0), reward_asset_deposit.amount
        elif reward_asset_deposit.type == TransactionType.AssetTransfer:
            return reward_asset_deposit.xfer_asset.id, reward_asset_deposit.asset_amount
        else:
            return UInt64(0), UInt64(0)
        
    @subroutine
    def get_logicsig_address(self, reward_asset: UInt64) -> Account:
        '''Derive the logicsig address for Tinyman pool from an asset ID / Algo'''
        program_bytes = self.pool_logicsig_template

        if reward_asset == 0:
            program_bytes = (
                program_bytes[0:3] + 
                arc4.UInt64(self.tinyman_router.id).bytes +
                arc4.UInt64(self.USDC).bytes +
                arc4.UInt64(reward_asset).bytes + 
                program_bytes[27:]
            )

        else:
            program_bytes = (
                program_bytes[0:3] + 
                arc4.UInt64(self.tinyman_router.id).bytes +
                arc4.UInt64(reward_asset).bytes +
                arc4.UInt64(0).bytes + 
                program_bytes[27:]
            )
            
        return Account.from_bytes(op.sha512_256(b'Program' + program_bytes))
    
    @subroutine
    def get_scaled_price(
        self,
        logicsig_address: Account
    ) -> BigUInt:
        '''Get the scaled price of an asset from the pool address' localstate against tinyman router'''
        asset_reserve = op.AppLocal.get_ex_uint64(logicsig_address, self.tinyman_router, b'asset_1_reserves')[0]
        algo_reserve = op.AppLocal.get_ex_uint64(logicsig_address, self.tinyman_router, b'asset_2_reserves')[0]

        SCALE_FACTOR = UInt64(1_000_000)

        return BigUInt(asset_reserve) * SCALE_FACTOR // algo_reserve
    
    # @subroutine
    # def sell_asset_portion(
    #     self, 
    #     reward_asset: UInt64, 
    #     reward_amount: UInt64, 
    #     reward_asset_tiny_pool_logicsig_address: Account,
    # ) -> tuple[UInt64, UInt64]:
    #     '''Calculate the amount of the asset to sell on pool creation'''
    #     fee_asset_amount = (reward_amount * 10) // 100

    #     transfer_asset_to_tinyman_pool_address = itxn.AssetTransfer(
    #         xfer_asset=reward_asset,
    #         asset_receiver=reward_asset_tiny_pool_logicsig_address,
    #         asset_amount=fee_asset_amount
    #     )

    #     arg_1 = Bytes(b'swap')
    #     arg_2 = Bytes(b'fixed-input')
    #     arg_3 = arc4.UInt64(0).bytes

    #     args = (arg_1, arg_2, arg_3)

    #     asset_fee_sell = itxn.ApplicationCall(
    #         app_id=self.tinyman_router,
    #         on_completion=OnCompleteAction.NoOp,
    #         app_args=args,
    #         accounts=(reward_asset_tiny_pool_logicsig_address,),
    #         assets=(Asset(reward_asset),)
    #     )

    #     tx_1, tx_2 = itxn.submit_txns(transfer_asset_to_tinyman_pool_address, asset_fee_sell)

    #     algo_received = arc4.UInt64.from_bytes(tx_2.logs(5)[-8:]).native
    #     reward_amount_after_fee = reward_amount - fee_asset_amount

    #     return algo_received, reward_amount_after_fee

    @subroutine
    def deploy_and_initialize_pool(
        self,
        asset_to_stake: UInt64, 
        reward_asset: UInt64,
        reward_amount: UInt64,
        pool_length: UInt64, 
        mbr_payment: gtxn.Transaction,
        creator: Account,
        server: String
    ) -> None:
        '''Create a pool and initialize globals for that pool'''
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)
        pre_mbr = get_mbr()

        new_pool = itxn.ApplicationCall(
            approval_program=self.pool_app_template.approval_program,
            clear_state_program=self.pool_app_template.clear_state_program,
            global_num_uint=15,
            global_num_bytes=15,
        ).submit().created_app


        itxn.Payment(
            receiver=new_pool.address,
            amount=Global.min_balance
        ).submit()

        inner_mbr_txn = itxn.Payment(
            receiver=new_pool.address,
            amount=Global.asset_opt_in_min_balance * 2
        )

        inner_mbr_cost, txn = abi_call(
            StakingPool.opt_into_assets,
            asset_to_stake,
            reward_asset,
            inner_mbr_txn,
            app_id=new_pool
        )

        if reward_asset == 0:
            inner_reward_asset_deposit = itxn.InnerTransaction(
                type=TransactionType.Payment,
                receiver=new_pool.address,
                amount=reward_amount
            )

        else:
            inner_reward_asset_deposit = itxn.InnerTransaction(
                type=TransactionType.AssetTransfer,
                xfer_asset=reward_asset,
                asset_amount=reward_amount,
                asset_receiver=new_pool.address
            )

        abi_call(
            StakingPool.initialize,
            asset_to_stake,
            inner_reward_asset_deposit,
            pool_length,
            server,
            self.REGISTRY_APP,
            Global.current_application_id,
            self.algofun_shares_app,
            self.tinyman_router,
            app_id=new_pool
        )

        self.create_box_ref_for_pool(
            server=server,
            asset_to_stake=asset_to_stake,
            reward_asset=reward_asset,
            reward_amount=reward_amount,
            pool_length=pool_length,
            new_pool_app_id=new_pool.id
        )

        post_mbr = get_mbr()
        mbr_cost = (post_mbr - pre_mbr) + Global.min_balance + inner_mbr_cost
        excess = mbr_payment.amount - mbr_cost
        itxn.Payment(
            receiver=creator,
            amount=excess,
            note='Excess MBR'
        ).submit()

    @subroutine
    def create_box_ref_for_pool(
        self,
        server: String,
        asset_to_stake: UInt64,
        reward_asset: UInt64,
        reward_amount: UInt64,
        pool_length: UInt64,
        new_pool_app_id: UInt64,

    ) -> None:
        
        
        pool_ref_box_email = PoolRefBoxName(
            server=server,
            asset_to_stake=arc4.UInt64(asset_to_stake),
            reward_asset=arc4.UInt64(reward_asset),
            reward_total=arc4.UInt64(reward_amount),
            pool_length=arc4.UInt64(pool_length)
        )

        pool_ref_box_value = PoolRefBoxValue(
            pool_app_id=arc4.UInt64(new_pool_app_id)
        )

        self.pool_refs[pool_ref_box_email] = pool_ref_box_value.copy()
        
    @abimethod
    def cleanse_ended_pool(self, pool_app_id: Application, pool_address_1: Account, pool_address_2: Account) -> None:
        '''Cleanse an ended pool'''
        assert Txn.sender == Global.creator_address
        abi_call(
            StakingPool.cleanse_ended_pool,
            pool_address_1,
            pool_address_2,
            app_id=pool_app_id
            
        )

    @abimethod(allow_actions=['UpdateApplication'])
    def update_pool(self, approval_program: Bytes, app_id: UInt64) -> None:
        '''Update a pool'''
        is_creator()
        itxn.ApplicationCall(
            approval_program=approval_program,
            clear_state_program=self.pool_app_template.clear_state_program,
            on_completion=OnCompleteAction.UpdateApplication,
            app_id=app_id,
        ).submit()

'''User stake data'''
class UserStake(Struct):
    stake_amount: arc4.UInt64
    last_acc_reward_per_share: arc4.UInt256

'''Staking Pool Contract 7/7 Contracts'''
class StakingPool(ARC4Contract):
    def __init__(self) -> None:
        self.asset_to_stake = UInt64(0)
        self.reward_asset = UInt64(0)
        self.initial_reward_total = UInt64(0)
        self.total_rewards = UInt64(0)
        self.pool_start_time = UInt64(0)
        self.pool_length = UInt64(0)
        self.reward_rate = UInt64(0)
        self.total_staked = UInt64(0)
        self.acc_reward_per_share = arc4.UInt256(0)
        self.last_update_time = UInt64(0)
        self.initialized  = False     
        self.SCALE = UInt64(1_000_000_000)   
        self.user_stake_instances = BoxMap(Account, UserStake, key_prefix='')
        self.platform_fee = UInt64(5)
        self.server = String()
        self.REGISTRY_APP_ID = Application()
        self.PSP_MANAGER_APP_ID = Application()
        self.TINYMAN_ROUTER = Application()
        self.users_staked = UInt64(0)
        self.algofun_shares_app = Application()


    @abimethod(allow_actions=['UpdateApplication', 'DeleteApplication'])
    def update_or_delete(self) -> None:
        '''Update or delete this contract if creator'''
        is_creator()

    @abimethod
    def opt_into_assets(self, asset_to_stake: UInt64, reward_asset: UInt64, mbr_payment: gtxn.Transaction) -> UInt64:
        '''Opt into stake asset and reward asset'''
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)
        self.not_initialized()

        pre_mbr = get_mbr()

        if asset_to_stake != 0:
            itxn.AssetTransfer(
                xfer_asset=asset_to_stake,
                asset_receiver=Global.current_application_address
            ).submit()

        if reward_asset != 0 and reward_asset != asset_to_stake:
            itxn.AssetTransfer(
                xfer_asset=reward_asset,
                asset_receiver=Global.current_application_address
            ).submit()

        post_mbr = get_mbr()
        mbr_cost = post_mbr - pre_mbr
        excess = mbr_payment.amount - mbr_cost
        refund_excess_mbr(excess)

        return mbr_cost


    @abimethod
    def initialize(
        self,
        asset_to_stake: UInt64,
        reward_asset_deposit: gtxn.Transaction,
        pool_length: UInt64, 
        server: String,
        registry_app: Application,
        psp_app: Application,
        algofun_shares_app: Application,
        tinyman_router: Application,
    ) -> None:
        '''Initialize this contract's globals'''
        self.server = server
        self.REGISTRY_APP = registry_app
        self.PSP_MANAGER_APP_ID = psp_app
        self.TINYMAN_ROUTER = tinyman_router
        self.algofun_shares_app = algofun_shares_app

        is_creator()
        self.not_initialized()
        self.asset_to_stake = asset_to_stake
        if reward_asset_deposit.type == TransactionType.Payment:
            self.reward_asset = UInt64(0)
            self.total_rewards = reward_asset_deposit.amount 
            self.initial_reward_total = reward_asset_deposit.amount

        else:
            self.reward_asset = reward_asset_deposit.xfer_asset.id
            self.total_rewards = reward_asset_deposit.asset_amount 
            self.initial_reward_total = reward_asset_deposit.asset_amount
            

        self.reward_rate = self.total_rewards // pool_length
        assert self.reward_rate != 0, "Reward rate is 0"
        self.pool_length = pool_length
        self.pool_start_time = Global.latest_timestamp
        self.last_update_time = Global.latest_timestamp

        self.initialized = True

    @subroutine
    def not_initialized(self) -> None:
        '''Check contract is not initialized (unnecessary modularization)'''
        assert self.initialized == False, "Contract is not initialized yet"

    @subroutine
    def is_initialized(self) -> None:
        '''Check contract is initialized (unnecessary modularization)'''
        assert self.initialized == True, "Contract is already initialized"

    @abimethod
    def stake(self, full_email: String, stake_axfer: gtxn.Transaction, mbr_payment: gtxn.Transaction) -> None:
        '''Stake some amount of an asset as a user'''
        self.users_staked += 1
        assert Global.latest_timestamp <= self.pool_start_time + self.pool_length, "Pool already ended"
        self.is_initialized()

        server = self.server
        assert full_email.bytes[-4:] == b'.avm', "Last 4 bytes are '.avm"
        at_symbol_index = full_email.bytes.length - server.bytes.length - 3
        assert full_email.bytes[at_symbol_index] == b'@', "@ symbol not at intended index of full email"
        server_index_start = at_symbol_index + 1
        assert full_email.bytes[server_index_start:-4] == server.bytes[2:], "Server bytes on full_email arg dont match server bytes in server arg"
        # valid full email, now check if it actually exists and the sender is the owner

        email_info, txn = abi_call(
            EmailRegistry.get_email_info_by_email,
            full_email,
            app_id=self.REGISTRY_APP
        )
        assert Txn.sender == email_info.account

        stake_amount = self.validate_stake_axfer(stake_axfer)
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)
        pre_mbr = get_mbr()
        self.update_user_instance(stake_amount)
        post_mbr = get_mbr()
        mbr_cost = post_mbr - pre_mbr
        excess = mbr_payment.amount - mbr_cost
        refund_excess_mbr(excess)


    @subroutine
    def validate_stake_axfer(self, stake_axfer: gtxn.Transaction) -> UInt64:
        '''Validate the stake application call's respective asset transfer'''
        contract_is_receiver(stake_axfer)
        if self.asset_to_stake == 0:
            stake_amount = stake_axfer.amount
            assert stake_axfer.type == TransactionType.Payment, "Invalid txn type for stake axfer where stake asset is algo"
            assert stake_amount != 0, "Attempting to send algo stake with 0 quantity"
        else:
            stake_amount = stake_axfer.asset_amount
            assert stake_axfer.type == TransactionType.AssetTransfer, "Invalid txn type for stake axfer where stake asset is ASA"
            assert stake_axfer.xfer_asset.id == self.asset_to_stake, "Stake axfer asset does not match asset_to_stake global"
            assert stake_amount != 0, "Attempting to send ASA stake with 0 quantity"

        return stake_amount

        

    @subroutine
    def update_user_instance(self, stake_amount: UInt64) -> None:
        '''Update a user's stake instance in box storage'''
        self.update_increment()                           

        if Txn.sender not in self.user_stake_instances:
            self.user_stake_instances[Txn.sender] = UserStake(
                stake_amount=arc4.UInt64(stake_amount),
                last_acc_reward_per_share=arc4.UInt256(self.acc_reward_per_share.native)
            )
        else:
            user = self.user_stake_instances[Txn.sender].copy()

            self.dispense_current_reward(user)

            user.stake_amount = arc4.UInt64(user.stake_amount.native + stake_amount)
            user.last_acc_reward_per_share  = arc4.UInt256(self.acc_reward_per_share.native)
            self.user_stake_instances[Txn.sender] = user.copy()

        self.total_staked += stake_amount
        
    @subroutine
    def create_new_user_stake_instance(self, stake_amount: UInt64) -> UserStake:
        '''Create a new user stake instance in box storage'''
        return UserStake(
            stake_amount=arc4.UInt64(stake_amount),
            last_acc_reward_per_share=self.acc_reward_per_share
        )
        
    @subroutine
    def dispense_current_reward(self, user: UserStake) -> UInt64:
        '''Dispense user's current reward'''
        reward_amount = op.btoi(
            (user.stake_amount.native * (self.acc_reward_per_share.native - user.last_acc_reward_per_share.native) // self.SCALE).bytes
        )

        if reward_amount == 0:
            return UInt64(0)

        if self.reward_asset == 0:
            itxn.Payment(
                receiver=Txn.sender,
                amount=reward_amount
            ).submit()
        else:
            itxn.AssetTransfer(
                xfer_asset=self.reward_asset,
                asset_amount=reward_amount,
                asset_receiver=Txn.sender
            ).submit()

        user.last_acc_reward_per_share = arc4.UInt256(self.acc_reward_per_share.native)

        return reward_amount

    @subroutine
    def update_increment(self) -> None:
        '''Update the accumulated increment'''
        if self.total_staked == 0:
            self.last_update_time = Global.latest_timestamp
            return  

        now = Global.latest_timestamp
        seconds_passed = now - self.last_update_time
        reward_delta   = seconds_passed * self.reward_rate 

        if reward_delta > self.total_rewards:
            reward_delta = self.total_rewards

        self.total_rewards -= reward_delta

        self.acc_reward_per_share = arc4.UInt256(
            self.acc_reward_per_share.native +
            arc4.UInt256(reward_delta * self.SCALE // self.total_staked).native
        )

        self.last_update_time = now

    @abimethod
    def unstake(self) -> UInt64:
        '''Unstake as a user'''
        self.update_increment()
        pre_mbr = get_mbr()
        user_stake_instance = self.user_stake_instances[Txn.sender].copy()
        staked_amount = user_stake_instance.stake_amount.native
    
        reward = self.dispense_current_reward(user_stake_instance)
        
        if self.asset_to_stake == 0:
            itxn.Payment(
                amount=staked_amount,
                receiver=Txn.sender,
            ).submit()

        else:
            itxn.AssetTransfer(
                xfer_asset=self.asset_to_stake,
                asset_amount=staked_amount,
                asset_receiver=Txn.sender
            ).submit()

        del self.user_stake_instances[Txn.sender]
        self.users_staked -= 1
        self.total_staked -= staked_amount
        post_mbr = get_mbr()
        excess = pre_mbr - post_mbr
        refund_excess_mbr(excess)

        return reward

    @abimethod
    def claim_reward(self) -> UInt64:
        '''Claim reward as a user'''
        self.update_increment()
        user_stake_instance = self.user_stake_instances[Txn.sender].copy()
        reward_amount = self.dispense_current_reward(user_stake_instance)
        user_stake_instance.last_acc_reward_per_share = self.acc_reward_per_share
        self.user_stake_instances[Txn.sender] = user_stake_instance.copy()
        return reward_amount


    @abimethod(allow_actions=['DeleteApplication'])
    def cleanse_ended_pool(self, pool_address_1: Account, pool_address_2: Account) -> None:
        '''Cleanse this contract's outstanding rewards after pool has ended'''
        is_creator()
        assert self.pool_start_time + self.pool_length < Global.latest_timestamp
        if self.asset_to_stake != 0:
            self.sell_remaining_asset(self.asset_to_stake, pool_address_1)

        if self.reward_asset != 0:
            self.sell_remaining_asset(self.reward_asset, pool_address_2)

        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=Global.current_application_address.balance
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )

        txn = abi_call(
            PrivateStakingPoolManager.delete_pool_box,
            Global.current_application_id,
            PoolRefBoxName(
                server=self.server,
                asset_to_stake=arc4.UInt64(self.asset_to_stake),
                reward_asset=arc4.UInt64(self.reward_asset),
                reward_total=arc4.UInt64(self.initial_reward_total),
                pool_length=arc4.UInt64(self.pool_length)
            ).bytes,
            app_id=self.PSP_MANAGER_APP_ID
        )


    @subroutine
    def sell_remaining_asset(self, asset: UInt64, pool_address: Account) -> None:
        '''Sell remaining asset as per above method'''
        transfer_asset_to_tinyman_pool_address = itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=pool_address,
            asset_amount=Asset(self.reward_asset).balance(Global.current_application_address)
        )

        arg_1 = Bytes(b'swap')
        arg_2 = Bytes(b'fixed-input')
        arg_3 = arc4.UInt64(0).bytes

        args = (arg_1, arg_2, arg_3)

        asset_fee_sell = itxn.ApplicationCall(
            app_id=self.TINYMAN_ROUTER,
            on_completion=OnCompleteAction.NoOp,
            app_args=args,
            accounts=(pool_address,),
            assets=(Asset(asset),)
        )

        tx_1, tx_2 = itxn.submit_txns(transfer_asset_to_tinyman_pool_address, asset_fee_sell)

        algo_received = arc4.UInt64.from_bytes(tx_2.logs(5)[-8:]).native

        fee_deposit = itxn.Payment(
            receiver=self.algofun_shares_app.address,
            amount=algo_received
        )

        abi_call(
            'add_fees(pay)void',
            fee_deposit,
            app_id=self.algofun_shares_app
        )
        asset_creator = Asset(asset).creator

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=asset_creator,
            asset_close_to=asset_creator,
        ).submit()