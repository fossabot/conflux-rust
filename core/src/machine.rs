// Copyright 2019 Conflux Foundation. All rights reserved.
// Conflux is free software and distributed under GNU General Public License.
// See http://www.gnu.org/licenses/

use super::builtin::Builtin;
use crate::vm::Spec;
use cfx_types::{Address, U256};
use primitives::CardinalNumber;
use std::{collections::BTreeMap, sync::Arc};

#[derive(Debug, PartialEq, Default)]
pub struct CommonParams {
    /// Account start nonce.
    pub account_start_nonce: U256,
    /// Maximum size of extra data.
    pub maximum_extra_data_size: usize,
    /// Network id.
    pub network_id: u64,
    /// Chain id.
    pub chain_id: u64,
    /// Main subprotocol name.
    pub subprotocol_name: String,
    /// Minimum gas limit.
    pub min_gas_limit: U256,
    /// Gas limit bound divisor (how much gas limit can change per block)
    pub gas_limit_bound_divisor: U256,
    /// Registrar contract address.
    pub registrar: Address,
    /// Node permission managing contract address.
    pub node_permission_contract: Option<Address>,
    /// Maximum contract code size that can be deployed.
    pub max_code_size: u64,
    /// Number of first block where max code size limit is active.
    pub max_code_size_transition: CardinalNumber,
    /// Maximum size of transaction's RLP payload.
    pub max_transaction_size: usize,
}

impl CommonParams {
    fn common_params() -> Self {
        CommonParams {
            account_start_nonce: 0x00.into(),
            maximum_extra_data_size: 0x20,
            network_id: 0x1,
            chain_id: 0x1,
            subprotocol_name: "cfx".into(),
            min_gas_limit: 0x1387.into(),
            gas_limit_bound_divisor: 0x0400.into(),
            registrar: "0xc6d9d2cd449a754c494264e1809c50e34d64562b".into(),
            node_permission_contract: None,
            max_code_size: 24576,
            max_code_size_transition: 0,
            max_transaction_size: 300 * 1024,
        }
    }
}

pub type SpecCreationRules = Fn(&mut Spec, CardinalNumber) + Sync + Send;

pub struct Machine {
    params: CommonParams,
    builtins: Arc<BTreeMap<Address, Builtin>>,
    spec_rules: Option<Box<SpecCreationRules>>,
}

impl Machine {
    pub fn builtin(
        &self, address: &Address, cardinal_number: CardinalNumber,
    ) -> Option<&Builtin> {
        self.builtins.get(address).and_then(|b| {
            if b.is_active(cardinal_number) {
                Some(b)
            } else {
                None
            }
        })
    }

    /// Attach special rules to the creation of spec.
    pub fn set_spec_creation_rules(&mut self, rules: Box<SpecCreationRules>) {
        self.spec_rules = Some(rules);
    }

    /// Get the general parameters of the chain.
    pub fn params(&self) -> &CommonParams { &self.params }

    pub fn spec(&self, number: CardinalNumber) -> Spec {
        let mut spec = Spec::new_spec();
        if let Some(ref rules) = self.spec_rules {
            (rules)(&mut spec, number)
        }
        spec
    }

    /// Builtin-contracts for the chain..
    pub fn builtins(&self) -> &BTreeMap<Address, Builtin> { &*self.builtins }
}

pub fn new_machine() -> Machine {
    Machine {
        params: CommonParams::common_params(),
        builtins: Arc::new(BTreeMap::new()),
        spec_rules: None,
    }
}
