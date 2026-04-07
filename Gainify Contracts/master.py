from algopy import (
    ARC4Contract, GlobalState,
    UInt64, Asset,
    Txn, String,
    op, Global,
    Application, gtxn,
    Account, OnCompleteAction,
    itxn, subroutine,
    BoxMap, TransactionType
)
from algopy.arc4 import (
    abimethod,
    abi_call,
    DynamicArray,
    Address,
    arc4_signature,
    Struct,
    Byte
)
from algopy.arc4 import UInt64 as arc4UInt64

'''
CREATORS: Leo / Allan / Ulrik
'''

class PoolRef(Struct):
    counter: arc4UInt64
    asset_a: arc4UInt64
    asset_b: arc4UInt64
    asset_c: arc4UInt64
    pool_type: Byte
    

class GainifyMasterApp(ARC4Contract):
    def __init__(self) -> None:
        '''Global States and Box Mappings'''
        self.POOLS_CREATED = GlobalState(UInt64(0)) 
        self.POOL_TEMPLATE_APP = GlobalState(Application) 
        self.CONTROLLER = GlobalState(Global.creator_address) 
        self.FEE_ADDRESS = GlobalState(Account) 
        self.COUNTER = GlobalState(UInt64(0))
        self.POOL_REF = BoxMap(
            PoolRef,
            arc4UInt64,
            key_prefix=""
        )
    
    @abimethod
    def return_counter(
        self
    ) -> UInt64:
        '''Get the current counter for the next pool reference's box name'''
        return self.COUNTER.value
    
    @abimethod()
    def designate_pool_template_global(
        self,
        poolTemplateApp: Application
    ) -> String:
        '''Designate the pool template app ID'''
        assert Txn.sender == self.CONTROLLER.value

        self.POOL_TEMPLATE_APP.value = poolTemplateApp

        return String("Pool Template Designated")
    
    
    @abimethod()
    def reassign_controller(
        self,
        assign_to: Address
    ) -> String:
        '''Reassign the controller for this master contract'''
        assert Txn.sender == self.CONTROLLER.value

        self.CONTROLLER.value = Account(assign_to.bytes)

        return String("Controller Designated")


    @abimethod()
    def opt_into_asset(
        self,
        asset_id: Asset,
    ) -> String:
        '''This method was used to opt into USDC, but can be used to opt into any asset'''
        
        assert Txn.sender == self.CONTROLLER.value

        itxn.AssetTransfer(
            asset_receiver=Global.current_application_address,
            xfer_asset=asset_id,
            fee=Global.min_txn_fee
        ).submit()
        
        return String("Opted into USDC")
    
    @abimethod()
    def designate_fee_address_global(
        self,
        assign_to: Address
    ) -> String:
        '''Designate the fee address for this master contract'''
        assert Txn.sender == self.CONTROLLER.value

        self.FEE_ADDRESS.value = Account(assign_to.bytes)

        return String("Fee Address Designated")

    @abimethod()
    def verify_gainify_nfd_ownership_master(
        self,
        address: Address,
        nfd_app_id: Application,
        tx_fee_payment: gtxn.PaymentTransaction
    ) -> bool:
        '''Verify that the user owns a gainify NFD'''
        assert tx_fee_payment.amount >= Global.min_txn_fee
        assert tx_fee_payment.receiver == Global.current_application_address

        result, txn = abi_call[DynamicArray[arc4UInt64]](
            'getAddressAppIds',
            address,
            app_id = UInt64(760937186),
            fee=Global.min_txn_fee
        )
        
        nfd_app_id_in_results = False
        
        for item in result:
            if item == nfd_app_id.id:
                nfd_app_id_in_results = True
                
        if nfd_app_id_in_results:
            nfd_name, state_exists = op.AppGlobal.get_ex_bytes(nfd_app_id, b'i.name')
            
            if nfd_name[-9:] == b'gain.algo' or nfd_name[-9] == b'afun.algo':
                return True
            
            else:
                return False
        else:
            return False
    
    @abimethod
    def opt_into_assets(self,
        stake_asset_id: UInt64,
        reward_asset_id: UInt64,
        supplemental_asset_id: UInt64,
        optin_payment: gtxn.PaymentTransaction
    ) -> UInt64:
        
        assert gtxn.ApplicationCallTransaction(6).app_args(0) == arc4_signature("create_staking_pool(uint64,uint64,string,string,string,txn,txn,pay,bool,axfer)(string,uint64)")
        assert stake_asset_id != UInt64(0)

        assets_opted = UInt64(0)
        LP_assets_need_optin = UInt64(0)
        stake_asset = Asset(stake_asset_id)

        if not Global.current_application_address.is_opted_in(stake_asset):
            itxn.AssetTransfer(
                asset_receiver=Global.current_application_address,
                xfer_asset=stake_asset,
                fee=Global.min_txn_fee
            ).submit()
            assets_opted += 1
            LP_assets_need_optin += 1

        if reward_asset_id != UInt64(0):
            LP_assets_need_optin += 1

            reward_asset = Asset(reward_asset_id)
            if not Global.current_application_address.is_opted_in(reward_asset):
                itxn.AssetTransfer(
                    asset_receiver=Global.current_application_address,
                    xfer_asset=reward_asset,
                    fee=Global.min_txn_fee
                ).submit()
                assets_opted += 1

        if supplemental_asset_id != UInt64(0):
            LP_assets_need_optin += 1
            assert supplemental_asset_id == 31566704
            supplemental_asset = Asset(supplemental_asset_id)
            if not Global.current_application_address.is_opted_in(supplemental_asset):
                itxn.AssetTransfer(
                    asset_receiver=Global.current_application_address,
                    xfer_asset=supplemental_asset,
                    fee=Global.min_txn_fee
                ).submit()
                assets_opted += 1

        optin_payment_required = assets_opted * 101_000
        assert optin_payment.amount >= optin_payment_required
        
        return LP_assets_need_optin * 101_000
                
                
    @subroutine
    def opt_out_assets(self,
        stake_asset_id: UInt64,
        reward_asset_id: UInt64,
    ) -> None:
        '''Opt out of the stake asset and reward asset (Not supplemental reward asset as requested) after they have been transferred'''
        if stake_asset_id != 31566704:
                itxn.AssetTransfer(
                    asset_receiver=Global.current_application_address,
                    asset_close_to=Asset(stake_asset_id).creator,
                    xfer_asset=stake_asset_id,
                    fee=Global.min_txn_fee
                ).submit()
                
        if reward_asset_id != 0 and reward_asset_id != 31566704:
                itxn.AssetTransfer(
                    asset_receiver=Global.current_application_address,
                    asset_close_to=Asset(reward_asset_id).creator,
                    xfer_asset=reward_asset_id,
                    fee=Global.min_txn_fee
                ).submit()     


    @abimethod
    def create_staking_pool(
        self,
        pool_length: UInt64,
        stake_asset: UInt64,
        website_link: String,
        discord_link: String,
        x_link: String,
        reward_asset_payment: gtxn.Transaction,
        supplemental_asset_payment: gtxn.Transaction,
        fee_payment: gtxn.PaymentTransaction,
        boost_toggled: bool,
        pool_launch_fee_usdc: gtxn.AssetTransferTransaction
    ) -> tuple[String, UInt64]:
        '''Initialize a staking pool with the parameters and assets provided'''
        self.POOLS_CREATED.value += 1
        assert fee_payment.amount == 1_500_000
        assert fee_payment.receiver == Global.current_application_address
        assert pool_launch_fee_usdc.xfer_asset.id == 31566704
        assert pool_launch_fee_usdc.asset_receiver == Global.current_application_address
        
        if boost_toggled == True:
            assert pool_launch_fee_usdc.asset_amount == 10_000_000
        elif boost_toggled == False:
            assert pool_launch_fee_usdc.asset_amount == 20_000_000
            
        itxn.AssetTransfer(
            xfer_asset=pool_launch_fee_usdc.xfer_asset.id,
            asset_receiver=self.FEE_ADDRESS.value,
            asset_amount=pool_launch_fee_usdc.asset_amount,
            fee=Global.min_txn_fee
        ).submit()
        
        LP_template = self.POOL_TEMPLATE_APP.value

        create_LP_contract = itxn.ApplicationCall(
            approval_program=LP_template.approval_program,
            clear_state_program=LP_template.clear_state_program,
            on_completion=OnCompleteAction.NoOp,
            global_num_uint=LP_template.global_num_uint,
            global_num_bytes=LP_template.global_num_bytes,
            fee=Global.min_txn_fee * 5,
            extra_program_pages=4
        ).submit()
        
        created_pool_app = create_LP_contract.created_app
        
        pass_fee_payment = itxn.Payment(
            receiver=created_pool_app.address,
            amount=arc4UInt64.from_bytes(gtxn.ApplicationCallTransaction(1).last_log[4:]).native + 201_000,
            fee=Global.min_txn_fee
        )

        if reward_asset_payment.type == TransactionType.Payment:
            reward_asset = UInt64(0)
        elif reward_asset_payment.type == TransactionType.AssetTransfer:
            reward_asset = reward_asset_payment.xfer_asset.id
            
        if supplemental_asset_payment.type == TransactionType.Payment:
            supplemental_asset = UInt64(0)
            supplemental_asset_amount = supplemental_asset_payment.amount
            
        elif supplemental_asset_payment.type == TransactionType.AssetTransfer:
            supplemental_asset = supplemental_asset_payment.xfer_asset.id
            supplemental_asset_amount = supplemental_asset_payment.asset_amount

            
        ignore_result = abi_call(
            "opt_into_assets(uint64,uint64,uint64,uint64,pay)void",
            stake_asset,
            reward_asset,
            supplemental_asset,
            supplemental_asset_amount,
            pass_fee_payment,
            app_id=created_pool_app,
            fee=Global.min_txn_fee
        )

        if reward_asset_payment.type == TransactionType.Payment:
            pass_reward_asset_payment = itxn.InnerTransaction(
                type=TransactionType.Payment,
                receiver=created_pool_app.address,
                amount=reward_asset_payment.amount,
                fee = Global.min_txn_fee
            )
            
        elif reward_asset_payment.type == TransactionType.AssetTransfer:
            pass_reward_asset_payment = itxn.InnerTransaction(
                type=TransactionType.AssetTransfer,
                xfer_asset=reward_asset_payment.xfer_asset,
                asset_receiver=created_pool_app.address,
                asset_amount=reward_asset_payment.asset_amount,
                fee=Global.min_txn_fee,
            )

        if supplemental_asset_payment.type == TransactionType.Payment:
            pass_supplemental_asset_payment = itxn.InnerTransaction(
                type=TransactionType.Payment,
                receiver=created_pool_app.address,
                amount=supplemental_asset_payment.amount,
                fee = Global.min_txn_fee
            )
            
        elif supplemental_asset_payment.type == TransactionType.AssetTransfer:
            pass_supplemental_asset_payment = itxn.InnerTransaction(
                type=TransactionType.AssetTransfer,
                xfer_asset=supplemental_asset_payment.xfer_asset,
                asset_receiver=created_pool_app.address,
                asset_amount=supplemental_asset_payment.asset_amount,
                fee=Global.min_txn_fee,
            )

        txn = abi_call(
            "initialize_staking_pool(uint64,uint64,txn,txn,string,string,string,bool,account,application)void",
            pool_length,
            stake_asset,
            pass_reward_asset_payment,
            pass_supplemental_asset_payment,
            website_link,
            discord_link,
            x_link,
            boost_toggled,
            self.FEE_ADDRESS.value,
            Global.current_application_id,
            app_id=create_LP_contract.created_app,
            fee=Global.min_txn_fee
        )
        
        self.opt_out_assets(stake_asset, reward_asset_payment.xfer_asset.id)
        if supplemental_asset_amount == 0:
            supplemental_asset = UInt64(1)

        creator = Asset(stake_asset).creator

        unit_name = Asset(stake_asset).unit_name
        if unit_name == b'SIPLP' or unit_name == b'PLP': #PACT LP
            pool_type = Byte(1)

        elif creator == 'XSKED5VKZZCSYNDWXZJI65JM2HP7HZFJWCOBIMOONKHTK5UVKENBNVDEYM': #TINY LP
            pool_type = Byte(2)

        else:
            pool_type = Byte(0)
                
        box_key = PoolRef(
            arc4UInt64(self.COUNTER.value),
            arc4UInt64(stake_asset),
            arc4UInt64(reward_asset),
            arc4UInt64(supplemental_asset),
            pool_type
        )

        self.POOL_REF[box_key] = arc4UInt64(created_pool_app.id)
        self.COUNTER.value += 1

        return String('Pool created for: '), stake_asset
    
    
    

    @abimethod(allow_actions=['UpdateApplication'])
    def update(
        self
    ) -> None:
        '''Update this master contract if sender is controller address'''
        assert Txn.sender == self.CONTROLLER.value
    
    

        
    @abimethod
    def call_restructure_boxes(
        self,
        pool_id: Application,
        mbr_pay: gtxn.PaymentTransaction
    ) -> None:
        '''
        This method was used to rectify a bug where box values exceeded 4096 bytes in length and could not
        be read regardless of the amount of box references used. This was an AVM limitation we did not have
        the foresight to anticipate with box maps. Admittedly, a benchmark where we overloaded boxes would 
        have been ideal here. However the project did not belong to us and we were paid *once* to create it, 
        and provided maintenance for free at no cost for some time. The issue did not arise until months after 
        we were already paid (which was not a substantial amount for 3 developers for several months) —
        the owners of the platform disappeared and left us with keys to core wallets for managing the contracts. 
        Although this method updated, and fixed that issue, a local state value assertion was accidentally added that 
        froze all staking pool contracts.
        '''
        assert Txn.sender == self.CONTROLLER.value
        
        cloned_mbr_pay = itxn.Payment(
            receiver=pool_id.address,
            amount=2_000_000
        )
        abi_call(
            'restructure_boxes(pay)void',
            cloned_mbr_pay,
            app_id=pool_id,
        )

        diff_send = Global.current_application_address.balance - Global.current_application_address.min_balance
        
        itxn.Payment(
            receiver=Txn.sender,
            amount=diff_send
        ).submit()


    @abimethod(allow_actions=['UpdateApplication', 'NoOp'])
    def update_staking_pool(
        self,
        staking_pool_to_update: Application,
    ) -> None:
        '''Update a specific staking pool by App ID'''
        assert Txn.sender == self.CONTROLLER.value

        LP_template = self.POOL_TEMPLATE_APP.value
        app_args = (arc4_signature("update()void"),)
        
        update_staking_pool_contract = itxn.ApplicationCall(
            app_args=app_args,
            approval_program=LP_template.approval_program,
            clear_state_program=LP_template.clear_state_program,
            on_completion=OnCompleteAction.UpdateApplication,
            fee=Global.min_txn_fee,
            app_id=staking_pool_to_update,
        ).submit()
        
