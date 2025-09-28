from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from wowchat.realm.big_number import BigNumber


@dataclass
class SRPClient:
	k: BigNumber = field(default_factory=lambda: BigNumber(3))
	a: BigNumber = field(default_factory=lambda: BigNumber.rand(19))
	A: BigNumber | None = None
	x: BigNumber | None = None
	M: BigNumber | None = None
	S: BigNumber | None = None
	K: BigNumber | None = None

	def generate_hash_logon_proof(self) -> bytes:
		assert self.A and self.M and self.K
		md = hashlib.sha1()
		md.update(self.A.as_byte_array(32))
		md.update(self.M.as_byte_array(20, reverse=False))
		md.update(self.K.as_byte_array(40))
		return md.digest()

	def step1(self, account: bytes, password: str, B: BigNumber, g: BigNumber, N: BigNumber, s: BigNumber) -> None:
		password_upper = password.upper()
		self.A = g.mod_pow(self.a, N)

		md = hashlib.sha1()
		md.update(self.A.as_byte_array(32))
		md.update(B.as_byte_array(32))
		u = BigNumber.from_bytes(bytearray(md.digest()), reverse=True)

		user = account + b":" + password_upper.encode("utf-8")
		md = hashlib.sha1()
		md.update(user)
		p = md.digest()

		md = hashlib.sha1()
		md.update(s.as_byte_array(32))
		md.update(p)
		x = BigNumber.from_bytes(bytearray(md.digest()), reverse=True)

		self.S = B.sub(g.mod_pow(x, N).mul(self.k)).mod_pow(self.a.add(u.mul(x)), N)  # type: ignore[union-attr]

		t = self.S.as_byte_array(32)
		t1 = bytes(t[0::2])
		t2 = bytes(t[1::2])
		vK = bytearray(40)

		md = hashlib.sha1()
		md.update(t1)
		digest = md.digest()
		for i in range(20):
			vK[i * 2] = digest[i]

		md = hashlib.sha1()
		md.update(t2)
		digest = md.digest()
		for i in range(20):
			vK[i * 2 + 1] = digest[i]

		md = hashlib.sha1()
		md.update(N.as_byte_array(32))
		hashN = bytearray(md.digest())

		md = hashlib.sha1()
		md.update(g.as_byte_array(1))
		digest = md.digest()
		for i in range(20):
			hashN[i] = hashN[i] ^ digest[i]

		md = hashlib.sha1()
		md.update(account)
		t4 = md.digest()

		self.K = BigNumber.from_bytes(vK, reverse=True)
		t3 = BigNumber.from_bytes(hashN, reverse=True)
		t4_correct = BigNumber.from_bytes(bytearray(t4), reverse=True)

		md = hashlib.sha1()
		md.update(t3.as_byte_array(20))
		md.update(t4_correct.as_byte_array(20))
		md.update(s.as_byte_array(32))
		md.update(self.A.as_byte_array(32))
		md.update(B.as_byte_array(32))
		md.update(self.K.as_byte_array(40))
		self.M = BigNumber.from_bytes(bytearray(md.digest()))