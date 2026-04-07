from algopy import (
    ARC4Contract, arc4, 
    UInt64, subroutine,
    Txn, Global,
    BoxMap, itxn,
    Asset, Account,
    gtxn, ensure_budget,
    OpUpFeeSource, Bytes,
    urange, op,
    BigUInt
)
from algopy.arc4 import abimethod, Struct, Bool


class SharesAssetDetails(Struct):
    asset_name: arc4.String
    asset_un: arc4.String
    total: arc4.UInt64
    decimals: arc4.UInt64
    url: arc4.String
    default_frozen: Bool
    reserve_address: arc4.Address

class UserShare(Struct):
    shares_quantity: arc4.UInt64
    shares_claimable: arc4.UInt64
    last_cumulative_reward_per_share: arc4.UInt256
    algo_claimed: arc4.UInt64


class AlgofunSharesSystem(ARC4Contract):
    def __init__(self) -> None:
        self.SHARES_INITIALIZED = Bool(False)
        self.SHARES_ASSET_ID = Asset()
        self.TOTAL_SHARES_UNITS = UInt64(0)
        self.INITIAL_VALUATION = UInt64(386_912)
        self.TEAM_SHARES = UInt64(0)
        self.SCALE_FACTOR = BigUInt(2**80)
        
        self.share_units_owned = UInt64(0)
        self.share_units_available = UInt64(0)
        
        self.share_owners = UInt64(0)
        self.user_shares = BoxMap(Account, UserShare, key_prefix='')
        self.fees_earned = UInt64(0)
        
        self.cumulative_reward_per_share = BigUInt(0)

    @abimethod(allow_actions=['UpdateApplication'])
    def update(self) -> None:
        '''Update contract if creator'''
        self.is_creator()

    @abimethod
    def create_shares(self, asset_info: SharesAssetDetails, mbr_payment: gtxn.PaymentTransaction) -> None:
        '''Create Shares ASA if creator and shares not initialized, configure globals~'''
        self.is_creator()
        self.contract_is_payment_receiver(txn=mbr_payment)
        self.shares_not_initialized()
        pre_mbr = self.get_mbr()

        self.SHARES_ASSET_ID = self.config_shares(asset_info=asset_info)
        self.set_initial_share_globals(asset_info=asset_info)
        self.set_initial_platform_share_amount()
        self.initialize_shares()

        post_mbr = self.get_mbr()
        self.refund_mbr(
            pre_mbr=pre_mbr,
            post_mbr=post_mbr,
            mbr_payment=mbr_payment,
        )

    @subroutine
    def is_creator(self) -> None:
        '''Check if sender is creator'''
        assert Txn.sender == Global.creator_address
  
    @subroutine
    def contract_is_payment_receiver(self, txn: gtxn.PaymentTransaction) -> None:
        '''Check if contract is payment receiver'''
        assert txn.receiver == Global.current_application_address

    @subroutine
    def shares_not_initialized(self) -> None:
        '''Check if shares are not initialized yet'''
        assert self.SHARES_INITIALIZED == False

    @subroutine
    def get_mbr(self) -> UInt64:
        '''Get the current MBR for this contract address'''
        return Global.current_application_address.min_balance
    
    @subroutine
    def config_shares(self, asset_info: SharesAssetDetails) -> Asset:
        '''Asset Configuration Txn for Shares ASA'''
        app_address = Global.current_application_address
    
        config_shares = itxn.AssetConfig(
            total=asset_info.total.native,
            unit_name=asset_info.asset_un.native,
            asset_name=asset_info.asset_name.native,
            decimals=asset_info.decimals.native,
            default_frozen=asset_info.default_frozen.native,
            url=asset_info.url.native,
            manager=app_address,
            reserve=asset_info.reserve_address.native,
            freeze=app_address,
            clawback=app_address,
        ).submit()

        return config_shares.created_asset

    @subroutine
    def get_current_app_address(self) -> Account:
        '''Get the current app address'''
        return Global.current_application_address
    
    @subroutine
    def set_initial_share_globals(self, asset_info: SharesAssetDetails) -> None:
        '''Set the initial share ASA details'''
        self.TOTAL_SHARES_UNITS = asset_info.total.native 
        self.share_units_available = self.TOTAL_SHARES_UNITS

    @subroutine
    def set_initial_platform_share_amount(self) -> None:
        '''Designate team shares'''
        self.TEAM_SHARES = ((self.TOTAL_SHARES_UNITS * 10) // 100)
        # self.TEAM_SHARES = ((self.TOTAL_SHARES_UNITS * enter % amount allocated to team here as integer between 0 and 100) // 100)
        self.add_shares_for_user(
            user=Global.current_application_address,
            share_amount=self.TEAM_SHARES,            
        )

    @subroutine
    def add_shares_for_user(
        self,
        user: Account,
        share_amount: UInt64,
    ) -> None:
        '''Add shares data for a user'''
        if user not in self.user_shares:
            self.user_shares[user] = UserShare(
                shares_quantity=arc4.UInt64(share_amount),
                shares_claimable=arc4.UInt64(share_amount),
                last_cumulative_reward_per_share=arc4.UInt256(self.cumulative_reward_per_share),
                algo_claimed=arc4.UInt64(0)
            )
            self.share_owners += 1

        else:
            user_shares = self.user_shares[user].copy()

            fees_generated, new_cumulative_reward_per_share = self.calculate_current_reward(user_shares)

            self.dispense_reward(fees_generated, user)

            user_shares.shares_quantity = arc4.UInt64(user_shares.shares_quantity.native + share_amount)
            user_shares.shares_claimable = arc4.UInt64(user_shares.shares_claimable.native + share_amount)
            user_shares.last_cumulative_reward_per_share = new_cumulative_reward_per_share
            user_shares.algo_claimed = arc4.UInt64(user_shares.algo_claimed.native + fees_generated)

            self.user_shares[user] = user_shares.copy()

        self.share_units_available -= share_amount
        self.share_units_owned +=  share_amount

    @subroutine
    def calculate_current_reward(
        self,
        user_shares: UserShare,
    ) -> tuple[UInt64, arc4.UInt256]:
        '''Calculate the users current reward'''
    
        delta = self.cumulative_reward_per_share - user_shares.last_cumulative_reward_per_share.native
        reward = (delta * user_shares.shares_quantity.native) // self.SCALE_FACTOR

        new_cumulative_reward_per_share = self.cumulative_reward_per_share

        # TODO ADD THIS BACK IN AFTER TESTING, FEES CLAIMED SHOULD NOT EXCEED FEES PAID FOR GROUP TXN
        total_fee_for_txn_group = self.get_total_fees_used_for_group()
        fees_generated = self.get_total_fees_used_for_group()
        assert fees_generated > total_fee_for_txn_group 

        return op.btoi(reward.bytes), arc4.UInt256(new_cumulative_reward_per_share)
    

    @subroutine
    def opup(self) -> None:
        '''Opup if budget below the base opcode budget [Box iterations can get heavy opcode usage]'''
        if Global.opcode_budget() < 700:
            ensure_budget(700, fee_source=OpUpFeeSource.GroupCredit)

    @subroutine
    def get_total_fees_used_for_group(self) -> UInt64:
        '''
        Get all fees used in this group transaction, user should not be claiming
        a miniscule award that costs more to claim than the actual reward
        '''
        total_fee_for_txn_group = UInt64(0)
        for index in urange(Global.group_size):
            total_fee_for_txn_group += gtxn.Transaction(index).fee
        return total_fee_for_txn_group

    @subroutine
    def dispense_reward(self, reward: UInt64, user: Account) -> None:
        '''Dispense the reward'''
        if user == Global.current_application_address:
            user = Txn.sender
        itxn.Payment(
            receiver=user,
            amount=reward,
            note=b'Reward Paid: ' + self.itoa(reward) + b'Microalgo' 
        ).submit()

    @subroutine
    def initialize_shares(self) -> None:
        '''Set shares initialized global to true, this should not have been modularized in hindsight'''
        self.SHARES_INITIALIZED = Bool(True)


    @subroutine
    def refund_mbr(
        self,
        pre_mbr: UInt64, 
        post_mbr: UInt64, 
        mbr_payment: gtxn.PaymentTransaction
    ) -> None:
        '''Calculate Excess MBR and refund'''
        diff = mbr_payment.amount - (post_mbr - pre_mbr)
        if diff > 1000:
            itxn.Payment(
                receiver=Txn.sender,
                amount=diff,
                note=b'Excess MBR Refunded: ' + self.itoa(diff) + b' Microalgo'
            ).submit()

    @subroutine
    def itoa(self, i: UInt64) -> Bytes:
        '''Convert integers to ascii characters to display integers in note fields'''
        digits = Bytes(b"0123456789")
        radix = digits.length
        if i < radix:
            return digits[i]
        return self.itoa(i // radix) + digits[i % radix]

    @abimethod
    def designate_shares(
        self, 
        user: Account, 
        share_amount: UInt64, 
        mbr_payment: gtxn.PaymentTransaction
    ) -> None:
        '''Designate shares for a user'''
        self.is_creator()
        self.shares_are_initialized()
        self.contract_is_payment_receiver(txn=mbr_payment)
        pre_mbr = self.get_mbr()
        self.add_shares_for_user(user=user, share_amount=share_amount)
        post_mbr = self.get_mbr()
        self.refund_mbr(
            pre_mbr=pre_mbr,
            post_mbr=post_mbr,
            mbr_payment=mbr_payment
        )

    @subroutine
    def shares_are_initialized(self) -> None:
        '''Check if shares are initialized'''
        assert self.SHARES_INITIALIZED == True

    @abimethod
    def claim_shares(self) -> None:
        '''Claim the actual shares ASA to wallet, the asset is frozen and no methods exist for trading at this time'''
        user_addr = Txn.sender
        assert user_addr in self.user_shares
        user_shares = self.user_shares[user_addr].copy()
        shares_claimable = user_shares.shares_claimable
        user_shares.shares_claimable = arc4.UInt64(0)
        self.dispense_shares(amount=shares_claimable)
        self.user_shares[user_addr] = user_shares.copy()
        
    @subroutine
    def dispense_shares(self, amount: arc4.UInt64) -> None:
        '''Transfer out ASA Shares to sender'''
        assert amount != 0
        self.unfreeze_user()
        itxn.AssetTransfer(
            xfer_asset=self.SHARES_ASSET_ID,
            asset_amount=amount.native,
            asset_receiver=Txn.sender,
            note=b"Claimed  " + self.itoa(amount.native // 10**6) + b" Algofun Shares" 
        ).submit()
        self.freeze_user()

    @subroutine
    def unfreeze_user(self) -> None:
        '''Unfreeze the ASA for this user temporarily'''
        itxn.AssetFreeze(
            freeze_asset=self.SHARES_ASSET_ID,
            freeze_account=Txn.sender,
            frozen=False,
        ).submit()
        
    @subroutine
    def freeze_user(self) -> None:
        '''Refreeze the ASA for this user'''
        itxn.AssetFreeze(
            freeze_asset=self.SHARES_ASSET_ID,
            freeze_account=Txn.sender,
            frozen=True,
        ).submit()


    @abimethod
    def add_fees(self, fee_deposit: gtxn.PaymentTransaction) -> None:
        '''This method can remain public, if someone wants to just dump 10 Algo + into the share system I don't think anyone would object'''
        # assert fee_dispense.amount > 10_000_000 Internal note, consider adding this line back in, as per last call loss per 1000 Algo is 6.4 + .375 Algo otherwise
        self.contract_is_payment_receiver(fee_deposit)
        increment = (fee_deposit.amount * self.SCALE_FACTOR) // self.share_units_owned
        self.cumulative_reward_per_share += increment
        self.fees_earned += fee_deposit.amount
    
    @abimethod
    def claim_fees(self) -> UInt64:
        '''Claim fees'''
        user = Txn.sender
        assert user in self.user_shares
        user_shares = self.user_shares[user].copy()
        fees_generated, new_cumulative_reward_per_share = self.calculate_current_reward(user_shares)
        self.dispense_reward(fees_generated, user)
        user_shares.last_cumulative_reward_per_share = new_cumulative_reward_per_share
        user_shares.algo_claimed = arc4.UInt64(user_shares.algo_claimed.native + fees_generated)
        self.user_shares[user] = user_shares.copy()
        return fees_generated

    @abimethod
    def creator_claim_fees(self) -> UInt64:
        '''Claim fees as creator'''
        self.is_creator()
        user = Global.current_application_address
        assert user in self.user_shares
        user_shares = self.user_shares[user].copy()
        fees_generated, new_cumulative_reward_per_share = self.calculate_current_reward(user_shares)
        self.dispense_reward(fees_generated, user)
        user_shares.last_cumulative_reward_per_share = new_cumulative_reward_per_share
        user_shares.algo_claimed = arc4.UInt64(user_shares.algo_claimed.native + fees_generated)
        self.user_shares[user] = user_shares.copy()
        return fees_generated
        
    @abimethod(readonly=True)
    def simulate_claim_fees(self, user: Account) -> UInt64:
        '''Read-only method for simulating fees earned so far for a user'''
        assert user in self.user_shares
        user_shares = self.user_shares[user].copy()
        fees_generated, new_cumulative_reward_per_share = self.calculate_current_reward(user_shares)
        return fees_generated
    
    @abimethod(readonly=True)
    def simulate_creator_claim_fees(self) -> UInt64:
        '''Read-only method for simulating fees earned so far for creator'''
        user = Global.current_application_address
        assert user in self.user_shares
        user_shares = self.user_shares[user].copy()
        fees_generated, new_cumulative_reward_per_share = self.calculate_current_reward(user_shares)
        return fees_generated