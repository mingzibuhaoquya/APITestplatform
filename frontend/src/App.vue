<template>
  <a-config-provider :locale="zhCN" :theme="appTheme">
    <div v-if="!me" class="login-page">
      <a-card class="login-card" :bordered="false">
        <div class="login-brand">
          <div class="login-logo"><img src="/company-logo.png" alt="测试平台" /></div>
          <div>
            <h1>测试平台</h1>
            <p>面向测试团队的接口回归与质量协作平台</p>
          </div>
        </div>
        <a-form layout="vertical" @submit.prevent="login">
          <a-form-item label="用户名">
            <a-input v-model:value="loginForm.username" size="large" placeholder="请输入用户名">
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>
          <a-form-item label="密码">
            <a-input-password v-model:value="loginForm.password" size="large" placeholder="请输入密码">
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>
          <a-button type="primary" html-type="submit" size="large" class="full" :loading="loginLoading">
            <template #icon><LoginOutlined /></template>
            登录
          </a-button>
        </a-form>
      </a-card>
    </div>

    <a-layout v-else class="shell">
      <a-layout-sider
        v-if="!isMobile"
        v-model:collapsed="sidebarCollapsed"
        :trigger="null"
        :collapsed-width="72"
        breakpoint="lg"
        width="232"
        class="app-sider"
        @breakpoint="handleSidebarBreakpoint"
      >
        <div class="brand" :class="{ 'brand-collapsed': sidebarCollapsed }">
          <img src="/company-logo.png" alt="测试平台" />
          <span v-if="!sidebarCollapsed">测试平台</span>
        </div>
        <a-menu :selected-keys="[active]" :default-open-keys="['interface-test', 'ui-tests']" mode="inline" @select="handleMenuSelect">
          <template v-for="item in visibleMenuGroups" :key="item.key">
            <a-sub-menu v-if="item.children?.length" :key="item.key">
              <template #icon><component :is="item.icon" /></template>
              <template #title>{{ item.label }}</template>
              <a-menu-item v-for="child in item.children" :key="child.key">
                <template #icon><component :is="child.icon" /></template>{{ child.label }}
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item v-else :key="item.key">
              <template #icon><component :is="item.icon" /></template>{{ item.label }}
            </a-menu-item>
          </template>
        </a-menu>
      </a-layout-sider>
      <a-drawer v-else v-model:open="mobileSidebarOpen" placement="left" :closable="false" :width="232" class="mobile-nav-drawer">
        <div class="brand"><img src="/company-logo.png" alt="测试平台" /><span>测试平台</span></div>
        <a-menu :selected-keys="[active]" :default-open-keys="['interface-test', 'ui-tests']" mode="inline" @select="handleMenuSelect">
          <template v-for="item in visibleMenuGroups" :key="item.key">
            <a-sub-menu v-if="item.children?.length" :key="item.key">
              <template #icon><component :is="item.icon" /></template>
              <template #title>{{ item.label }}</template>
              <a-menu-item v-for="child in item.children" :key="child.key">
                <template #icon><component :is="child.icon" /></template>{{ child.label }}
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item v-else :key="item.key">
              <template #icon><component :is="item.icon" /></template>{{ item.label }}
            </a-menu-item>
          </template>
        </a-menu>
      </a-drawer>
      <a-layout
        class="main-layout"
        :class="{ 'main-layout-collapsed': sidebarCollapsed, 'main-layout-mobile': isMobile }"
      >
        <a-layout-header class="app-header">
          <div class="header-left">
            <a-button type="text" class="sidebar-trigger" @click="toggleSidebar">
              <template #icon><MenuUnfoldOutlined v-if="sidebarCollapsed || isMobile" /><MenuFoldOutlined v-else /></template>
            </a-button>
            <a-divider type="vertical" />
            <div class="header-page-title">
              <span class="header-eyebrow">测试工作台</span>
              <strong>{{ currentPageTitle }}</strong>
            </div>
          </div>
          <a-dropdown trigger="click">
            <button class="user-menu-trigger">
              <a-avatar :size="32" class="user-avatar">{{ avatarText }}</a-avatar>
              <span class="user-menu-name">{{ me.username }}</span>
              <DownOutlined class="user-menu-arrow" />
            </button>
            <template #overlay>
              <a-menu class="user-dropdown-menu">
                <a-menu-item key="changePassword" @click="handleUserCommand('changePassword')"><template #icon><LockOutlined /></template>修改密码</a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleUserCommand('logout')"><template #icon><LogoutOutlined /></template>退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-layout-header>
      <div class="tabs-bar">
        <a-tabs
          v-model:active-key="active"
          type="editable-card"
          hide-add
          @edit="handleTabEdit"
        >
          <a-tab-pane
            v-for="tab in openedTabs"
            :key="tab.name"
            :tab="tab.label"
            :closable="tab.closable"
          />
        </a-tabs>
      </div>
      <a-layout-content>
        <section v-if="active === 'dashboard'" class="dashboard-page">
          <div class="page-heading dashboard-heading">
            <div><h1>数据概览</h1><p>掌握平台配置规模与最近执行概况</p></div>
            <a-button type="default" @click="loadAll"><template #icon><ReloadOutlined /></template>刷新数据</a-button>
          </div>
          <div class="grid">
            <a-card v-for="stat in dashboardStats" :key="stat.label" class="stat-card" :class="`stat-${stat.tone}`" :bordered="false">
              <div class="stat-card-icon"><component :is="stat.icon" /></div>
              <a-statistic :title="stat.label" :value="stat.value" />
              <div class="stat-card-meta">{{ stat.description }}</div>
            </a-card>
          </div>
        </section>

        <section v-if="active === 'accounts'" class="page-view">
          <div class="toolbar"><h2>用户管理</h2><a-button v-if="me.role === 'admin'" type="primary" @click="openCreateUserDialog"><template #icon><UserAddOutlined /></template>创建测试人员</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="用户名">
              <a-input v-model:value="userSearch.username" placeholder="请输入用户名" allow-clear @keyup.enter="searchUsers" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="userSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchUsers">搜索</a-button>
              <a-button @click="resetUserSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="users">
            <a-table-column data-index="username" title="用户名" />
            <a-table-column data-index="real_name" title="姓名" />
            <a-table-column title="角色">
              <template #default="{ record: row }">{{ row.role_name || row.role }}</template>
            </a-table-column>
            <a-table-column title="状态">
              <template #default="{ record: row }">
                <a-tag :color="row.status === 'active' ? 'success' : 'warning'">
                  {{ statusText(row.status) }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" width="220" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditUserDialog(row)">编辑</a-button>
                  <a-button
                    size="small"
                    :type="row.status === 'active' ? 'default' : 'primary'"
                    @click="toggleUserStatus(row)"
                  >
                    {{ row.status === 'active' ? '禁用' : '启用' }}
                  </a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="userPagination.page"
              :page-size="userPagination.pageSize"
              :total="userPagination.total"
              @change="changeUserPage"
            />
          </div>

          <a-modal v-model:open="createUserDialogVisible" title="创建账号" width="420px" @after-close="resetUserForm">
            <a-form layout="vertical" @submit.prevent="createUser">
              <a-form-item label="用户名">
                <a-input v-model:value="userForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="姓名">
                <a-input v-model:value="userForm.real_name" placeholder="请输入姓名" />
              </a-form-item>
              <a-form-item label="角色">
                <a-select v-model:value="userForm.role" placeholder="请选择角色">
                  <a-select-option v-for="role in roles" :key="role.code" :value="role.code">{{ role.name }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateUser">取消</a-button>
              <a-button type="primary" @click="createUser">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editUserDialogVisible" title="编辑账号" width="420px" @after-close="resetEditUserForm">
            <a-form layout="vertical" @submit.prevent="updateUser">
              <a-form-item label="用户名">
                <a-input v-model:value="editUserForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="姓名">
                <a-input v-model:value="editUserForm.real_name" placeholder="请输入姓名" />
              </a-form-item>
              <a-form-item label="角色">
                <a-select v-model:value="editUserForm.role" placeholder="请选择角色">
                  <a-select-option v-for="role in roles" :key="role.code" :value="role.code">{{ role.name }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditUser">取消</a-button>
              <a-button type="primary" @click="updateUser">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'roles'" class="page-view">
          <div class="toolbar"><h2>角色管理</h2><a-button type="primary" @click="openCreateRoleDialog"><template #icon><PlusOutlined /></template>新增角色</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="角色名称">
              <a-input v-model:value="roleSearch.name" placeholder="请输入角色名称" allow-clear @keyup.enter="searchRoles" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="roleSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchRoles">搜索</a-button>
              <a-button @click="resetRoleSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="roles">
            <a-table-column data-index="code" title="角色编码" width="150" />
            <a-table-column data-index="name" title="角色名称" width="150" />
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'warning'">{{ statusText(row.status) }}</a-tag></template>
            </a-table-column>
            <a-table-column title="操作" width="230" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openRolePermissionDialog(row)">菜单权限</a-button>
                  <a-button size="small" @click="openEditRoleDialog(row)">编辑</a-button>
                  <a-button size="small" danger :disabled="row.is_builtin || row.user_count > 0" @click="deleteRole(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination :show-total="paginationTotal" show-less-items :current="rolePagination.page" :page-size="rolePagination.pageSize" :total="rolePagination.total" @change="changeRolePage" />
          </div>

          <a-modal v-model:open="createRoleDialogVisible" title="新增角色" width="640px" @after-close="resetRoleForm">
            <a-form layout="vertical" @submit.prevent="createRole">
              <a-form-item label="角色编码"><a-input v-model:value="roleForm.code" placeholder="例如: reviewer" /></a-form-item>
              <a-form-item label="角色名称"><a-input v-model:value="roleForm.name" placeholder="请输入角色名称" /></a-form-item>
              <a-form-item label="描述"><a-textarea v-model:value="roleForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="请输入描述" /></a-form-item>
              <a-form-item label="状态">
                <a-select v-model:value="roleForm.status">
                  <a-select-option value="active">启用</a-select-option>
                  <a-select-option value="disabled">禁用</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="菜单权限">
                <a-checkbox-group v-model:value="roleForm.menus" class="menu-permission-group">
                  <template v-for="group in roleMenus" :key="group.key">
                    <div v-if="group.children?.length" class="menu-permission-section">
                      <strong>{{ group.label }}</strong>
                      <a-checkbox v-for="child in group.children" :key="child.key" :value="child.key">{{ child.label }}</a-checkbox>
                    </div>
                    <a-checkbox v-else :value="group.key">{{ group.label }}</a-checkbox>
                  </template>
                </a-checkbox-group>
              </a-form-item>
            </a-form>
            <template #footer><a-button @click="cancelCreateRole">取消</a-button><a-button type="primary" @click="createRole">确认</a-button></template>
          </a-modal>

          <a-modal v-model:open="editRoleDialogVisible" title="编辑角色" width="640px" @after-close="resetEditRoleForm">
            <a-form layout="vertical" @submit.prevent="updateRole">
              <a-form-item label="角色编码"><a-input v-model:value="editRoleForm.code" disabled /></a-form-item>
              <a-form-item label="角色名称"><a-input v-model:value="editRoleForm.name" placeholder="请输入角色名称" /></a-form-item>
              <a-form-item label="描述"><a-textarea v-model:value="editRoleForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="请输入描述" /></a-form-item>
              <a-form-item label="状态">
                <a-select v-model:value="editRoleForm.status">
                  <a-select-option value="active">启用</a-select-option>
                  <a-select-option value="disabled">禁用</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="菜单权限">
                <a-checkbox-group v-model:value="editRoleForm.menus" class="menu-permission-group">
                  <template v-for="group in roleMenus" :key="group.key">
                    <div v-if="group.children?.length" class="menu-permission-section">
                      <strong>{{ group.label }}</strong>
                      <a-checkbox v-for="child in group.children" :key="child.key" :value="child.key">{{ child.label }}</a-checkbox>
                    </div>
                    <a-checkbox v-else :value="group.key">{{ group.label }}</a-checkbox>
                  </template>
                </a-checkbox-group>
              </a-form-item>
            </a-form>
            <template #footer><a-button @click="cancelEditRole">取消</a-button><a-button type="primary" @click="updateRole">确认</a-button></template>
          </a-modal>

          <a-modal v-model:open="rolePermissionDialogVisible" title="菜单权限" width="560px" @after-close="resetRolePermissionForm">
            <div class="role-permission-role">角色：{{ rolePermissionForm.name }}</div>
            <a-tree
              v-model:checked-keys="rolePermissionForm.menus"
              class="role-permission-tree"
              checkable
              block-node
              default-expand-all
              :tree-data="roleMenuTreeData"
            />
            <template #footer><a-button @click="cancelRolePermission">取消</a-button><a-button type="primary" @click="saveRolePermissions">确认</a-button></template>
          </a-modal>
        </section>

        <section v-if="active === 'tickets'" class="page-view">
          <div class="toolbar"><h2>工单管理</h2><a-button type="primary" @click="openCreateTicket"><template #icon><PlusOutlined /></template>提交工单</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="工单标题"><a-input v-model:value="ticketSearch.title" placeholder="请输入工单标题" allow-clear @keyup.enter="searchTickets" /></a-form-item>
            <a-form-item label="工单类型"><a-select v-model:value="ticketSearch.category" placeholder="请选择类型" allow-clear><a-select-option value="feature">功能建议</a-select-option><a-select-option value="issue">问题反馈</a-select-option><a-select-option value="experience">体验优化</a-select-option><a-select-option value="other">其他</a-select-option></a-select></a-form-item>
            <a-form-item label="状态"><a-select v-model:value="ticketSearch.status" placeholder="请选择状态" allow-clear><a-select-option value="pending">待处理</a-select-option><a-select-option value="processing">处理中</a-select-option><a-select-option value="resolved">已解决</a-select-option></a-select></a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchTickets">搜索</a-button><a-button @click="resetTickets">重置</a-button></div>
          </a-form>
          <a-table :pagination="false" :data-source="tickets" :scroll="{ x: 1120 }">
            <a-table-column title="编号" width="70"><template #default="{ index }">{{ (ticketPagination.page - 1) * ticketPagination.pageSize + index + 1 }}</template></a-table-column>
            <a-table-column title="类型" width="110"><template #default="{ record: row }">{{ ticketCategoryText(row.category) }}</template></a-table-column>
            <a-table-column title="工单标题"><template #default="{ record: row }"><TableText :value="row.title" /></template></a-table-column>
            <a-table-column title="状态" width="100"><template #default="{ record: row }"><a-tag :color="ticketStatusColor(row.status)">{{ ticketStatusText(row.status) }}</a-tag></template></a-table-column>
            <a-table-column data-index="submitter_name" title="提交人" width="120" />
            <a-table-column data-index="create_date" title="提交时间" width="170" />
            <a-table-column data-index="handler_name" title="处理人" width="120" />
            <a-table-column data-index="handled_at" title="处理时间" width="170" />
            <a-table-column title="操作" width="90" fixed="right"><template #default="{ record: row }"><a-button size="small" @click="openTicketDetail(row)">查看</a-button></template></a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="ticketPagination.page" :page-size="ticketPagination.pageSize" :total="ticketPagination.total" @change="changeTicketPage" /></div>

          <a-modal v-model:open="createTicketVisible" title="提交工单" width="640px" @after-close="resetTicketForm">
            <a-form layout="vertical"><a-form-item label="工单类型" required><a-select v-model:value="ticketForm.category"><a-select-option value="feature">功能建议</a-select-option><a-select-option value="issue">问题反馈</a-select-option><a-select-option value="experience">体验优化</a-select-option><a-select-option value="other">其他</a-select-option></a-select></a-form-item><a-form-item label="工单标题" required><a-input v-model:value="ticketForm.title" :maxlength="200" show-count /></a-form-item><a-form-item label="建议内容" required><a-textarea v-model:value="ticketForm.content" :maxlength="5000" show-count :auto-size="{ minRows: 5, maxRows: 9 }" /></a-form-item><a-form-item label="附件"><a-upload v-model:file-list="ticketForm.files" :before-upload="validateTicketFile" :max-count="5" multiple><a-button><template #icon><FileTextOutlined /></template>选择附件</a-button></a-upload><div class="form-tip">最多 5 个附件，单个文件不超过 20MB。</div></a-form-item></a-form>
            <template #footer><a-button @click="createTicketVisible = false">取消</a-button><a-button type="primary" :loading="ticketSubmitting" @click="submitTicket">提交</a-button></template>
          </a-modal>

          <a-modal v-model:open="ticketDetailVisible" title="工单详情" width="720px">
            <a-descriptions v-if="ticketDetail" :column="2" bordered size="small"><a-descriptions-item label="工单类型">{{ ticketCategoryText(ticketDetail.category) }}</a-descriptions-item><a-descriptions-item label="状态"><a-tag :color="ticketStatusColor(ticketDetail.status)">{{ ticketStatusText(ticketDetail.status) }}</a-tag></a-descriptions-item><a-descriptions-item label="工单标题" :span="2">{{ ticketDetail.title }}</a-descriptions-item><a-descriptions-item label="建议内容" :span="2"><div class="ticket-content">{{ ticketDetail.content }}</div></a-descriptions-item><a-descriptions-item label="附件" :span="2"><a-space v-if="ticketDetail.attachments?.length" wrap><a-button v-for="item in ticketDetail.attachments" :key="item.id" type="link" size="small" @click="downloadTicketAttachment(ticketDetail, item)">{{ item.name }}</a-button></a-space><span v-else>-</span></a-descriptions-item><a-descriptions-item label="处理人">{{ ticketDetail.handler_name || '-' }}</a-descriptions-item><a-descriptions-item label="处理时间">{{ ticketDetail.handled_at || '-' }}</a-descriptions-item><a-descriptions-item label="处理回复" :span="2"><div class="ticket-content">{{ ticketDetail.reply || '-' }}</div></a-descriptions-item></a-descriptions>
            <template #footer><a-button @click="ticketDetailVisible = false">关闭</a-button><a-button v-if="me?.role === 'admin'" type="primary" @click="openProcessTicket">处理工单</a-button></template>
          </a-modal>
          <a-modal v-model:open="processTicketVisible" title="处理工单" width="560px"><a-form layout="vertical"><a-form-item label="状态"><a-select v-model:value="ticketProcessForm.status"><a-select-option value="processing">处理中</a-select-option><a-select-option value="resolved">已解决</a-select-option></a-select></a-form-item><a-form-item label="处理回复" :required="ticketProcessForm.status === 'resolved'"><a-textarea v-model:value="ticketProcessForm.reply" :maxlength="5000" :auto-size="{ minRows: 4, maxRows: 8 }" /></a-form-item></a-form><template #footer><a-button @click="processTicketVisible = false">取消</a-button><a-button type="primary" @click="saveTicketProcess">确认</a-button></template></a-modal>
        </section>

        <section v-if="active === 'api_key_configs'" class="page-view">
          <div class="toolbar"><h2>API Key配置</h2><a-button type="primary" @click="openCreateApiKeyConfig"><template #icon><PlusOutlined /></template>新增配置</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="关键字"><a-input v-model:value="apiKeyConfigSearch.keyword" placeholder="请输入中文名或环境变量名" allow-clear @keyup.enter="searchApiKeyConfigs" /></a-form-item>
            <a-form-item label="状态"><a-select v-model:value="apiKeyConfigSearch.status" placeholder="请选择状态" allow-clear><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchApiKeyConfigs">搜索</a-button><a-button @click="resetApiKeyConfigSearch">重置</a-button></div>
          </a-form>
          <a-table class="app-data-table" :pagination="false" :data-source="apiKeyConfigList" :scroll="{ x: true }">
            <a-table-column title="编号" width="52"><template #default="{ index }">{{ apiKeyConfigSerialNumber(index) }}</template></a-table-column>
            <a-table-column data-index="display_name" title="中文名" width="190" />
            <a-table-column title="环境变量名"><template #default="{ record: row }"><TableText :value="row.env_key" /></template></a-table-column>
            <a-table-column title="环境变量状态" width="130"><template #default="{ record: row }"><a-tag :color="row.configured ? 'success' : 'warning'">{{ row.configured ? '已配置' : '未配置' }}</a-tag></template></a-table-column>
            <a-table-column title="状态" width="90"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'warning'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
            <a-table-column title="备注"><template #default="{ record: row }"><TableText :value="row.description" /></template></a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="150" fixed="right"><template #default="{ record: row }"><div class="table-actions"><a-button size="small" @click="openEditApiKeyConfig(row)">编辑</a-button><a-button size="small" danger @click="deleteApiKeyConfig(row)">删除</a-button></div></template></a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="apiKeyConfigPagination.page" :page-size="apiKeyConfigPagination.pageSize" :total="apiKeyConfigPagination.total" @change="changeApiKeyConfigPage" /></div>

          <a-modal v-model:open="apiKeyConfigFormVisible" :title="apiKeyConfigForm.id ? '编辑API Key配置' : '新增API Key配置'" width="560px" @after-close="resetApiKeyConfigForm">
            <a-alert type="info" show-icon message="这里只维护环境变量名和中文名，不保存、不展示真实 API Key。" class="modal-alert" />
            <a-form layout="vertical">
              <a-form-item label="中文名" required><a-input v-model:value="apiKeyConfigForm.display_name" placeholder="例如：FAF知识库问答工作流Key" /></a-form-item>
              <a-form-item label="环境变量名" required><a-input v-model:value="apiKeyConfigForm.env_key" placeholder="例如：DIFY_WORKFLOW_API_KEY_FAF" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="apiKeyConfigForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="备注"><a-textarea v-model:value="apiKeyConfigForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="可记录用途、归属知识库或维护人" /></a-form-item>
            </a-form>
            <template #footer><a-button @click="apiKeyConfigFormVisible = false">取消</a-button><a-button type="primary" @click="saveApiKeyConfig">确认</a-button></template>
          </a-modal>
        </section>
        <section v-if="active === 'projects'" class="page-view">
          <div class="toolbar"><h2>项目管理</h2><a-button type="primary" @click="openCreateProjectDialog"><template #icon><PlusOutlined /></template>创建项目</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目名称">
              <a-input v-model:value="projectSearch.name" placeholder="请输入项目名称" allow-clear @keyup.enter="searchProjects" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchProjects">搜索</a-button>
              <a-button @click="resetProjectSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="projectList">
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="描述"><template #default="{ record: row }"><TableText :value="row.description" /></template></a-table-column>
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditProjectDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteProject(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="projectPagination.page"
              :page-size="projectPagination.pageSize"
              :total="projectPagination.total"
              @change="changeProjectPage"
            />
          </div>

          <a-modal v-model:open="createProjectDialogVisible" title="创建项目" width="420px" @after-close="resetProjectForm">
            <a-form layout="vertical" @submit.prevent="createProject">
              <a-form-item label="项目名称">
                <a-input v-model:value="projectForm.name" placeholder="请输入项目名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-input v-model:value="projectForm.description" placeholder="请输入描述" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateProject">取消</a-button>
              <a-button type="primary" @click="createProject">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editProjectDialogVisible" title="编辑项目" width="420px" @after-close="resetEditProjectForm">
            <a-form layout="vertical" @submit.prevent="updateProject">
              <a-form-item label="项目名称">
                <a-input v-model:value="editProjectForm.name" placeholder="请输入项目名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-input v-model:value="editProjectForm.description" placeholder="请输入描述" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditProject">取消</a-button>
              <a-button type="primary" @click="updateProject">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'environments'" class="page-view">
          <div class="toolbar"><h2>环境管理</h2><a-button type="primary" @click="openCreateEnvironmentDialog"><template #icon><PlusOutlined /></template>新增环境</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="environmentSearch.project_id" placeholder="请选择项目" allow-clear>
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="环境名称">
              <a-input v-model:value="environmentSearch.name" placeholder="请输入环境名称" allow-clear @keyup.enter="searchEnvironments" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchEnvironments">搜索</a-button>
              <a-button @click="resetEnvironmentSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="environmentList">
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="环境名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column data-index="protocol" title="协议" />
            <a-table-column title="Base URL"><template #default="{ record: row }"><TableText :value="row.base_url" /></template></a-table-column>
            <a-table-column data-index="port" title="端口号" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditEnvironmentDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteEnvironment(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="environmentPagination.page"
              :page-size="environmentPagination.pageSize"
              :total="environmentPagination.total"
              @change="changeEnvironmentPage"
            />
          </div>

          <a-modal v-model:open="createEnvironmentDialogVisible" title="新增环境" width="420px" @after-close="resetEnvironmentForm">
            <a-form layout="vertical" @submit.prevent="createEnvironment">
              <a-form-item label="项目">
                <a-select v-model:value="envForm.project_id" placeholder="请选择项目">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境名称">
                <a-input v-model:value="envForm.name" placeholder="请输入环境名称" />
              </a-form-item>
              <a-form-item label="协议">
                <a-select v-model:value="envForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(envForm.protocol)">
                <a-select-option value="http">http</a-select-option>
                <a-select-option value="https">https</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Base URL">
                <a-input v-model:value="envForm.base_url" placeholder="请输入 Base URL" />
              </a-form-item>
              <a-form-item label="端口号">
                <a-input v-model:value="envForm.port" placeholder="请输入端口号" @input="envForm.port = digitsOnly(envForm.port)" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateEnvironment">取消</a-button>
              <a-button type="primary" @click="createEnvironment">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editEnvironmentDialogVisible" title="编辑环境" width="420px" @after-close="resetEditEnvironmentForm">
            <a-form layout="vertical" @submit.prevent="updateEnvironment">
              <a-form-item label="项目">
                <a-select v-model:value="editEnvironmentForm.project_id" placeholder="请选择项目">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境名称">
                <a-input v-model:value="editEnvironmentForm.name" placeholder="请输入环境名称" />
              </a-form-item>
              <a-form-item label="协议">
                <a-select v-model:value="editEnvironmentForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(editEnvironmentForm.protocol)">
                  <a-select-option value="http">http</a-select-option>
                  <a-select-option value="https">https</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Base URL">
                <a-input v-model:value="editEnvironmentForm.base_url" placeholder="请输入 Base URL" />
              </a-form-item>
              <a-form-item label="端口号">
                <a-input v-model:value="editEnvironmentForm.port" placeholder="请输入端口号" @input="editEnvironmentForm.port = digitsOnly(editEnvironmentForm.port)" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditEnvironment">取消</a-button>
              <a-button type="primary" @click="updateEnvironment">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'apis'" class="page-view">
          <div class="toolbar"><h2>接口管理</h2><a-button type="primary" @click="openCreateApiDialog"><template #icon><PlusOutlined /></template>新增接口</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="apiSearch.project_id" placeholder="请选择项目" allow-clear>
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="名称">
              <a-input v-model:value="apiSearch.name" placeholder="请输入接口名称" allow-clear @keyup.enter="searchApis" />
            </a-form-item>
            <a-form-item label="URL名称">
              <a-input v-model:value="apiSearch.url" placeholder="请输入接口路径" allow-clear @keyup.enter="searchApis" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchApis">搜索</a-button>
              <a-button @click="resetApiSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="apiList">
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="接口描述"><template #default="{ record: row }"><TableText :value="row.description" /></template></a-table-column>
            <a-table-column data-index="method" title="方法" width="100" />
            <a-table-column title="路径"><template #default="{ record: row }"><TableText :value="row.path" /></template></a-table-column>
            <a-table-column data-index="create_date" title="创建时间" width="170" />
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditApiDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteApi(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="apiPagination.page"
              :page-size="apiPagination.pageSize"
              :total="apiPagination.total"
              @change="changeApiPage"
            />
          </div>

        </section>

        <section v-if="active === 'mocks'" class="page-view">
          <div class="toolbar"><h2>Mock服务</h2><a-button type="primary" @click="openCreateMockDialog"><template #icon><PlusOutlined /></template>新增Mock</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="mockSearch.project_id" placeholder="请选择项目" allow-clear @change="changeMockSearchProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="环境">
              <a-select v-model:value="mockSearch.environment_id" placeholder="请先选择项目" allow-clear :disabled="!mockSearch.project_id">
                <a-select-option v-for="e in mockSearchEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="名称">
              <a-input v-model:value="mockSearch.name" placeholder="请输入Mock名称" allow-clear @keyup.enter="searchMocks" />
            </a-form-item>
            <a-form-item label="路径">
              <a-input v-model:value="mockSearch.path" placeholder="请输入Mock路径" allow-clear @keyup.enter="searchMocks" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="mockSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchMocks">搜索</a-button>
              <a-button @click="resetMockSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="mockList">
            <a-table-column data-index="project_name" title="项目" />
            <a-table-column data-index="environment_name" title="环境" />
            <a-table-column data-index="name" title="名称" />
            <a-table-column data-index="method" title="方法" width="90" />
            <a-table-column data-index="path" title="路径" />
            <a-table-column title="Mock绝对路径" width="380">
              <template #default="{ record: row }">
                <a-typography-text copyable class="mock-url-text">{{ mockAbsoluteUrl(row) }}</a-typography-text>
              </template>
            </a-table-column>
              <a-table-column data-index="status_code" title="HTTP状态码" width="120" />
              <a-table-column title="SM3签名" width="110">
                <template #default="{ record: row }">
                  <a-tag :color="row.sm3_enabled ? 'processing' : 'default'">{{ row.sm3_enabled ? '启用' : '关闭' }}</a-tag>
                </template>
              </a-table-column>
              <a-table-column title="状态" width="100">
                <template #default="{ record: row }">
                  <a-tag :color="row.status === 'active' ? 'success' : 'default'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="240" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditMockDialog(row)">编辑</a-button>
                  <a-button size="small" @click="toggleMockStatus(row)">{{ row.status === 'active' ? '禁用' : '启用' }}</a-button>
                  <a-button size="small" danger @click="deleteMock(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="mockPagination.page"
              :page-size="mockPagination.pageSize"
              :total="mockPagination.total"
              @change="changeMockPage"
            />
          </div>

          <a-modal v-model:open="createMockDialogVisible" title="新增Mock" width="900px" @after-close="resetMockForm">
            <a-form layout="vertical" class="form-grid" @submit.prevent="createMock">
              <a-form-item label="项目">
                <a-select v-model:value="mockForm.project_id" placeholder="请选择项目" @change="changeMockFormProject">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境">
                <a-select v-model:value="mockForm.environment_id" placeholder="请先选择项目" :disabled="!mockForm.project_id">
                  <a-select-option v-for="e in mockFormEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Mock名称">
                <a-input v-model:value="mockForm.name" placeholder="请输入Mock名称" />
              </a-form-item>
              <a-form-item label="方法">
                <a-select v-model:value="mockForm.method">
                  <a-select-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="路径" class="wide">
                <a-input v-model:value="mockForm.path" placeholder="/api/example" />
              </a-form-item>
              <a-form-item label="Mock绝对路径" class="wide">
                <a-input :value="mockAbsoluteUrl(mockForm)" readonly placeholder="选择环境并填写路径后自动生成" />
              </a-form-item>
              <a-form-item label="状态">
                <a-select v-model:value="mockForm.status">
                  <a-select-option value="active">启用</a-select-option>
                  <a-select-option value="disabled">禁用</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="HTTP状态码">
                <a-input v-model:value="mockForm.status_code" placeholder="200" @input="mockForm.status_code = digitsOnly(mockForm.status_code)" />
              </a-form-item>
                <a-form-item label="延迟(ms)">
                  <a-input v-model:value="mockForm.delay_ms" placeholder="0" @input="mockForm.delay_ms = digitsOnly(mockForm.delay_ms)" />
                </a-form-item>
                <a-form-item label="SM3签名">
                  <a-checkbox v-model:checked="mockForm.sm3_enabled">启用后返回Body尾部自动追加SM3</a-checkbox>
                </a-form-item>
                <a-form-item label="备注" class="wide">
                  <a-textarea v-model:value="mockForm.description" :rows="2" placeholder="请输入备注" />
                </a-form-item>
              <div class="wide">
                <div class="kv-title">
                  <h4>响应Header</h4>
                  <a-button size="small" @click="addMockHeaderRow">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="mockForm.headerRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="Content-Type" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="application/json" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeMockHeaderRow($index)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </div>
              <a-form-item label="响应Body格式">
                <a-radio-group v-model:value="mockForm.body_format" @change="changeMockBodyFormat(mockForm)">
                  <a-radio-button value="json">json</a-radio-button>
                  <a-radio-button value="xml">xml</a-radio-button>
                  <a-radio-button value="text">text</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <div class="wide">
                <div class="body-editor-head">
                  <span>响应Body</span>
                  <a-button size="small" @click="formatMockBody(mockForm)">格式化</a-button>
                </div>
                <BodyCodeEditor
                  v-model="mockForm.response_body"
                  :language="mockForm.body_format"
                  :placeholder="mockBodyPlaceholder(mockForm.body_format)"
                  min-height="260px"
                />
              </div>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateMock">取消</a-button>
              <a-button type="primary" @click="createMock">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editMockDialogVisible" title="编辑Mock" width="900px" @after-close="resetEditMockForm">
            <a-form layout="vertical" class="form-grid" @submit.prevent="updateMock">
              <a-form-item label="项目">
                <a-select v-model:value="editMockForm.project_id" placeholder="请选择项目" @change="changeEditMockFormProject">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境">
                <a-select v-model:value="editMockForm.environment_id" placeholder="请先选择项目" :disabled="!editMockForm.project_id">
                  <a-select-option v-for="e in editMockFormEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Mock名称">
                <a-input v-model:value="editMockForm.name" placeholder="请输入Mock名称" />
              </a-form-item>
              <a-form-item label="方法">
                <a-select v-model:value="editMockForm.method">
                  <a-select-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="路径" class="wide">
                <a-input v-model:value="editMockForm.path" placeholder="/api/example" />
              </a-form-item>
              <a-form-item label="Mock绝对路径" class="wide">
                <a-input :value="mockAbsoluteUrl(editMockForm)" readonly placeholder="选择环境并填写路径后自动生成" />
              </a-form-item>
              <a-form-item label="状态">
                <a-select v-model:value="editMockForm.status">
                  <a-select-option value="active">启用</a-select-option>
                  <a-select-option value="disabled">禁用</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="HTTP状态码">
                <a-input v-model:value="editMockForm.status_code" placeholder="200" @input="editMockForm.status_code = digitsOnly(editMockForm.status_code)" />
              </a-form-item>
                <a-form-item label="延迟(ms)">
                  <a-input v-model:value="editMockForm.delay_ms" placeholder="0" @input="editMockForm.delay_ms = digitsOnly(editMockForm.delay_ms)" />
                </a-form-item>
                <a-form-item label="SM3签名">
                  <a-checkbox v-model:checked="editMockForm.sm3_enabled">启用后返回Body尾部自动追加SM3</a-checkbox>
                </a-form-item>
                <a-form-item label="备注" class="wide">
                  <a-textarea v-model:value="editMockForm.description" :rows="2" placeholder="请输入备注" />
                </a-form-item>
              <div class="wide">
                <div class="kv-title">
                  <h4>响应Header</h4>
                  <a-button size="small" @click="addEditMockHeaderRow">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="editMockForm.headerRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="Content-Type" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="application/json" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeEditMockHeaderRow($index)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </div>
              <a-form-item label="响应Body格式">
                <a-radio-group v-model:value="editMockForm.body_format" @change="changeMockBodyFormat(editMockForm)">
                  <a-radio-button value="json">json</a-radio-button>
                  <a-radio-button value="xml">xml</a-radio-button>
                  <a-radio-button value="text">text</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <div class="wide">
                <div class="body-editor-head">
                  <span>响应Body</span>
                  <a-button size="small" @click="formatMockBody(editMockForm)">格式化</a-button>
                </div>
                <BodyCodeEditor
                  v-model="editMockForm.response_body"
                  :language="editMockForm.body_format"
                  :placeholder="mockBodyPlaceholder(editMockForm.body_format)"
                  min-height="260px"
                />
              </div>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditMock">取消</a-button>
              <a-button type="primary" @click="updateMock">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'ui-cases'" class="page-view">
          <div class="toolbar">
            <h2>UI用例管理</h2>
            <div class="toolbar-actions">
              <a-button @click="openAiSettingDialog">AI配置</a-button>
              <a-button type="primary" @click="openCreateUiCaseDialog"><template #icon><PlusOutlined /></template>新增UI用例</a-button>
            </div>
          </div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="uiCaseSearch.project_id" placeholder="请选择项目" allow-clear @change="changeUiCaseSearchProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="环境">
              <a-select v-model:value="uiCaseSearch.environment_id" placeholder="请先选择项目" allow-clear :disabled="!uiCaseSearch.project_id">
                <a-select-option v-for="e in uiCaseSearchEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="名称"><a-input v-model:value="uiCaseSearch.name" placeholder="请输入UI用例名称" allow-clear @keyup.enter="searchUiCases" /></a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="uiCaseSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchUiCases">搜索</a-button><a-button @click="resetUiCaseSearch">重置</a-button></div>
          </a-form>
          <a-table class="ui-case-table" :pagination="false" :data-source="uiCaseList" :scroll="{ x: 1420 }">
            <a-table-column data-index="project_name" title="项目" width="160" />
            <a-table-column data-index="environment_name" title="环境" width="160" />
            <a-table-column data-index="name" title="UI用例名称" width="220" />
            <a-table-column title="目标地址" width="300"><template #default="{ record: row }"><span class="url-cell">{{ row.start_url }}</span></template></a-table-column>
            <a-table-column title="模式" width="130">
              <template #default="{ record: row }">
                <a-select :value="row.execution_mode === 'ai' ? 'ai' : 'advanced'" size="small" style="width: 104px" @change="changeUiCaseMode(row, $event)">
                  <a-select-option value="ai">AI模式</a-select-option>
                  <a-select-option value="advanced">高级模式</a-select-option>
                </a-select>
              </template>
            </a-table-column>
            <a-table-column title="浏览器" width="120"><template #default="{ record: row }">{{ uiBrowserChannelText(row.browser_channel) }}</template></a-table-column>
            <a-table-column title="步骤数" width="90"><template #default="{ record: row }">{{ row.execution_mode === 'ai' ? (row.max_steps || 30) : (row.steps || []).length }}</template></a-table-column>
            <a-table-column title="状态" width="100"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'default'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
            <a-table-column title="最近执行" width="110"><template #default="{ record: row }"><a-tag :color="executionStatusColor(row.last_status)">{{ executionStatusText(row.last_status) }}</a-tag></template></a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="190" />
            <a-table-column title="操作" width="260" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" type="primary" @click="executeUiCase(row)">执行</a-button>
                  <a-button v-if="uiExecutionCanStop(row.last_status)" size="small" danger @click="stopUiExecution(row)">停止</a-button>
                  <a-button size="small" @click="openEditUiCaseDialog(row)">编辑</a-button>
                  <a-button size="small" @click="openUiExecutionDetail(row)">详情</a-button>
                  <a-button size="small" danger @click="deleteUiCase(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="uiCasePagination.page" :page-size="uiCasePagination.pageSize" :total="uiCasePagination.total" @change="changeUiCasePage" /></div>

          <a-modal v-model:open="createUiCaseDialogVisible" title="新增UI用例" width="1100px" @after-close="resetUiCaseForm">
            <a-form layout="vertical" class="form-grid" @submit.prevent="createUiCase">
              <a-form-item label="项目"><a-select v-model:value="uiCaseForm.project_id" placeholder="请选择项目" @change="changeUiCaseFormProject"><a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="环境"><a-select v-model:value="uiCaseForm.environment_id" placeholder="请先选择项目" :disabled="!uiCaseForm.project_id"><a-select-option v-for="e in uiCaseFormEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="用例名称"><a-input v-model:value="uiCaseForm.name" placeholder="请输入UI用例名称" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="uiCaseForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器"><a-select v-model:value="uiCaseForm.browser_channel"><a-select-option value="chromium">Playwright Chromium</a-select-option><a-select-option value="chrome">本机 Chrome</a-select-option><a-select-option value="msedge">本机 Edge</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器模式"><a-select v-model:value="uiCaseForm.headless"><a-select-option :value="true">无头模式</a-select-option><a-select-option :value="false">有头模式</a-select-option></a-select></a-form-item>
              <a-form-item label="页面等待"><a-select v-model:value="uiCaseForm.wait_until"><a-select-option value="networkidle">网络空闲</a-select-option><a-select-option value="load">页面加载完成</a-select-option><a-select-option value="domcontentloaded">DOM加载完成</a-select-option></a-select></a-form-item>
              <a-form-item label="额外等待(ms)"><a-input-number v-model:value="uiCaseForm.wait_after_load_ms" :min="0" :max="60000" :step="500" style="width: 100%" /></a-form-item>
              <a-form-item label="目标地址" class="wide"><a-input v-model:value="uiCaseForm.start_url" placeholder="/login 或完整 URL" /></a-form-item>
              <a-form-item label="用例模式" class="wide">
                <a-radio-group v-model:value="uiCaseForm.execution_mode">
                  <a-radio-button value="ai">AI模式</a-radio-button>
                  <a-radio-button value="advanced">高级模式</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <template v-if="uiCaseForm.execution_mode === 'ai'">
                <a-form-item label="测试目标" class="wide"><a-textarea v-model:value="uiCaseForm.test_goal" :rows="4" placeholder="例如：登录系统后进入合同列表，按合同编号查询详情，并确认页面展示合同信息" /></a-form-item>
                <a-form-item label="测试数据" class="wide"><a-textarea v-model:value="uiCaseForm.test_data_text" :rows="5" placeholder="{&#10;  &quot;用户名&quot;: &quot;test&quot;,&#10;  &quot;密码&quot;: &quot;123456&quot;,&#10;  &quot;合同编号&quot;: &quot;HT001&quot;&#10;}" /></a-form-item>
                <a-form-item label="期望结果" class="wide"><a-textarea v-model:value="uiCaseForm.assertion_goal" :rows="3" placeholder="例如：页面出现合同编号，且状态为正常" /></a-form-item>
                <a-form-item label="最大步骤数"><a-input-number v-model:value="uiCaseForm.max_steps" :min="1" :max="100" style="width: 100%" /></a-form-item>
                <a-form-item label="单步超时(ms)"><a-input-number v-model:value="uiCaseForm.step_timeout_ms" :min="1000" :max="120000" :step="1000" style="width: 100%" /></a-form-item>
                <a-form-item label="允许AI操作"><a-switch v-model:checked="uiCaseForm.allow_ai_actions" checked-children="允许" un-checked-children="只观察" /></a-form-item>
                <a-alert class="wide compact-alert" type="info" show-icon message="AI模式会在受控浏览器中观察当前页面，并在点击、输入、选择、断言等安全动作中选择下一步；每一步都会保存原因、截图和执行结果。" />
              </template>
              <a-form-item label="描述" class="wide"><a-textarea v-model:value="uiCaseForm.description" :rows="2" placeholder="请输入用例说明" /></a-form-item>
              <div v-if="uiCaseForm.execution_mode === 'advanced'" class="wide">
                <div class="kv-title">
                  <h4>测试步骤</h4>
                  <div class="toolbar-actions">
                    <a-button size="small" @click="openAiStepDialog(uiCaseForm)">自然语言生成</a-button>
                    <a-button size="small" @click="startUiStepRecorder(uiCaseForm)">录制添加步骤</a-button>
                    <a-button size="small" @click="addUiStep(uiCaseForm)">添加步骤</a-button>
                  </div>
                </div>
                <a-alert class="compact-alert" type="info" show-icon message="定位方式选择“AI描述”时，目标元素可填写自然语言，例如：点击登录按钮、填写用户名输入框；执行时会自动转换为可执行定位器。" />
                <a-table :pagination="false" :data-source="uiCaseForm.steps" :row-key="(row: UiStepRow) => row.id" :scroll="{ x: 1100 }">
                  <a-table-column title="动作" width="170"><template #default="{ record: row }"><a-select v-model:value="row.action" :popup-match-select-width="false" popup-class-name="ui-action-dropdown"><a-select-option value="goto">打开页面</a-select-option><a-select-option value="click">点击</a-select-option><a-select-option value="dblclick">双击</a-select-option><a-select-option value="fill">输入</a-select-option><a-select-option value="select">选择</a-select-option><a-select-option value="wait">等待</a-select-option><a-select-option value="assert_text">断言文本</a-select-option><a-select-option value="assert_visible">断言元素</a-select-option><a-select-option value="screenshot">截图</a-select-option></a-select></template></a-table-column>
                  <a-table-column title="定位方式" width="170"><template #default="{ record: row }"><a-select v-model:value="row.locator_type" :popup-match-select-width="false" popup-class-name="ui-locator-dropdown"><a-select-option value="css">CSS</a-select-option><a-select-option value="xpath">XPath</a-select-option><a-select-option value="text">文本</a-select-option><a-select-option value="placeholder">占位符</a-select-option><a-select-option value="role">按钮文字</a-select-option><a-select-option value="ai">AI描述</a-select-option></a-select></template></a-table-column>
                  <a-table-column title="目标元素/地址" width="260"><template #default="{ record: row }"><a-input v-model:value="row.target" placeholder="CSS、XPath、文本，或写：点击登录按钮" /></template></a-table-column>
                  <a-table-column title="值/期望" width="220"><template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="如 VIN${random.string(14)}，或等待毫秒" /></template></a-table-column>
                  <a-table-column title="说明" width="220"><template #default="{ record: row }"><a-input v-model:value="row.description" placeholder="步骤说明" /></template></a-table-column>
                  <a-table-column title="操作" width="230" fixed="right"><template #default="{ record: row, index }"><div class="table-actions"><a-button size="small" @click="startUiElementPicker(uiCaseForm, row)">拾取</a-button><a-button size="small" @click="moveUiStep(uiCaseForm, index, -1)">上移</a-button><a-button size="small" @click="moveUiStep(uiCaseForm, index, 1)">下移</a-button><a-button size="small" danger @click="removeUiStep(uiCaseForm, index)">删除</a-button></div></template></a-table-column>
                </a-table>
              </div>
            </a-form>
            <template #footer><a-button @click="createUiCaseDialogVisible = false">取消</a-button><a-button type="primary" @click="createUiCase">确认</a-button></template>
          </a-modal>

          <a-modal v-model:open="editUiCaseDialogVisible" title="编辑UI用例" width="1100px" @after-close="resetEditUiCaseForm">
            <a-form layout="vertical" class="form-grid" @submit.prevent="updateUiCase">
              <a-form-item label="项目"><a-select v-model:value="editUiCaseForm.project_id" placeholder="请选择项目" @change="changeEditUiCaseFormProject"><a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="环境"><a-select v-model:value="editUiCaseForm.environment_id" placeholder="请先选择项目" :disabled="!editUiCaseForm.project_id"><a-select-option v-for="e in editUiCaseFormEnvironments" :key="e.id" :value="e.id">{{ e.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="用例名称"><a-input v-model:value="editUiCaseForm.name" placeholder="请输入UI用例名称" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="editUiCaseForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器"><a-select v-model:value="editUiCaseForm.browser_channel"><a-select-option value="chromium">Playwright Chromium</a-select-option><a-select-option value="chrome">本机 Chrome</a-select-option><a-select-option value="msedge">本机 Edge</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器模式"><a-select v-model:value="editUiCaseForm.headless"><a-select-option :value="true">无头模式</a-select-option><a-select-option :value="false">有头模式</a-select-option></a-select></a-form-item>
              <a-form-item label="页面等待"><a-select v-model:value="editUiCaseForm.wait_until"><a-select-option value="networkidle">网络空闲</a-select-option><a-select-option value="load">页面加载完成</a-select-option><a-select-option value="domcontentloaded">DOM加载完成</a-select-option></a-select></a-form-item>
              <a-form-item label="额外等待(ms)"><a-input-number v-model:value="editUiCaseForm.wait_after_load_ms" :min="0" :max="60000" :step="500" style="width: 100%" /></a-form-item>
              <a-form-item label="目标地址" class="wide"><a-input v-model:value="editUiCaseForm.start_url" placeholder="/login 或完整 URL" /></a-form-item>
              <a-form-item label="用例模式" class="wide">
                <a-radio-group v-model:value="editUiCaseForm.execution_mode">
                  <a-radio-button value="ai">AI模式</a-radio-button>
                  <a-radio-button value="advanced">高级模式</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <template v-if="editUiCaseForm.execution_mode === 'ai'">
                <a-form-item label="测试目标" class="wide"><a-textarea v-model:value="editUiCaseForm.test_goal" :rows="4" placeholder="例如：登录系统后进入合同列表，按合同编号查询详情，并确认页面展示合同信息" /></a-form-item>
                <a-form-item label="测试数据" class="wide"><a-textarea v-model:value="editUiCaseForm.test_data_text" :rows="5" placeholder="{&#10;  &quot;用户名&quot;: &quot;test&quot;,&#10;  &quot;密码&quot;: &quot;123456&quot;,&#10;  &quot;合同编号&quot;: &quot;HT001&quot;&#10;}" /></a-form-item>
                <a-form-item label="期望结果" class="wide"><a-textarea v-model:value="editUiCaseForm.assertion_goal" :rows="3" placeholder="例如：页面出现合同编号，且状态为正常" /></a-form-item>
                <a-form-item label="最大步骤数"><a-input-number v-model:value="editUiCaseForm.max_steps" :min="1" :max="100" style="width: 100%" /></a-form-item>
                <a-form-item label="单步超时(ms)"><a-input-number v-model:value="editUiCaseForm.step_timeout_ms" :min="1000" :max="120000" :step="1000" style="width: 100%" /></a-form-item>
                <a-form-item label="允许AI操作"><a-switch v-model:checked="editUiCaseForm.allow_ai_actions" checked-children="允许" un-checked-children="只观察" /></a-form-item>
                <a-alert class="wide compact-alert" type="info" show-icon message="AI模式会在受控浏览器中观察当前页面，并在点击、输入、选择、断言等安全动作中选择下一步；每一步都会保存原因、截图和执行结果。" />
              </template>
              <a-form-item label="描述" class="wide"><a-textarea v-model:value="editUiCaseForm.description" :rows="2" placeholder="请输入用例说明" /></a-form-item>
              <div v-if="editUiCaseForm.execution_mode === 'advanced'" class="wide">
                <div class="kv-title">
                  <h4>测试步骤</h4>
                  <div class="toolbar-actions">
                    <a-button size="small" @click="openAiStepDialog(editUiCaseForm)">自然语言生成</a-button>
                    <a-button size="small" @click="startUiStepRecorder(editUiCaseForm)">录制添加步骤</a-button>
                    <a-button size="small" @click="addUiStep(editUiCaseForm)">添加步骤</a-button>
                  </div>
                </div>
                <a-alert class="compact-alert" type="info" show-icon message="定位方式选择“AI描述”时，目标元素可填写自然语言，例如：点击登录按钮、填写用户名输入框；执行时会自动转换为可执行定位器。" />
                <a-table :pagination="false" :data-source="editUiCaseForm.steps" :row-key="(row: UiStepRow) => row.id" :scroll="{ x: 1100 }">
                  <a-table-column title="动作" width="170"><template #default="{ record: row }"><a-select v-model:value="row.action" :popup-match-select-width="false" popup-class-name="ui-action-dropdown"><a-select-option value="goto">打开页面</a-select-option><a-select-option value="click">点击</a-select-option><a-select-option value="dblclick">双击</a-select-option><a-select-option value="fill">输入</a-select-option><a-select-option value="select">选择</a-select-option><a-select-option value="wait">等待</a-select-option><a-select-option value="assert_text">断言文本</a-select-option><a-select-option value="assert_visible">断言元素</a-select-option><a-select-option value="screenshot">截图</a-select-option></a-select></template></a-table-column>
                  <a-table-column title="定位方式" width="170"><template #default="{ record: row }"><a-select v-model:value="row.locator_type" :popup-match-select-width="false" popup-class-name="ui-locator-dropdown"><a-select-option value="css">CSS</a-select-option><a-select-option value="xpath">XPath</a-select-option><a-select-option value="text">文本</a-select-option><a-select-option value="placeholder">占位符</a-select-option><a-select-option value="role">按钮文字</a-select-option><a-select-option value="ai">AI描述</a-select-option></a-select></template></a-table-column>
                  <a-table-column title="目标元素/地址" width="260"><template #default="{ record: row }"><a-input v-model:value="row.target" placeholder="CSS、XPath、文本，或写：点击登录按钮" /></template></a-table-column>
                  <a-table-column title="值/期望" width="220"><template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="如 VIN${random.string(14)}，或等待毫秒" /></template></a-table-column>
                  <a-table-column title="说明" width="220"><template #default="{ record: row }"><a-input v-model:value="row.description" placeholder="步骤说明" /></template></a-table-column>
                  <a-table-column title="操作" width="230" fixed="right"><template #default="{ record: row, index }"><div class="table-actions"><a-button size="small" @click="startUiElementPicker(editUiCaseForm, row)">拾取</a-button><a-button size="small" @click="moveUiStep(editUiCaseForm, index, -1)">上移</a-button><a-button size="small" @click="moveUiStep(editUiCaseForm, index, 1)">下移</a-button><a-button size="small" danger @click="removeUiStep(editUiCaseForm, index)">删除</a-button></div></template></a-table-column>
                </a-table>
              </div>
            </a-form>
            <template #footer><a-button @click="editUiCaseDialogVisible = false">取消</a-button><a-button type="primary" @click="updateUiCase">确认</a-button></template>
          </a-modal>
        </section>

          <a-modal v-model:open="aiStepDialogVisible" title="自然语言生成步骤" width="860px" @cancel="resetAiStepGenerator">
            <a-form layout="vertical">
              <a-form-item label="执行描述">
                <a-textarea
                  v-model:value="aiStepGenerator.prompt"
                  :rows="5"
                  placeholder="例如：打开登录页，输入用户名 testyan1，输入密码 123456，选择经销商伊犁金帝汽车服务有限公司，点击登录，断言看到首页"
                />
              </a-form-item>
              <a-form-item label="应用方式">
                <a-radio-group v-model:value="aiStepGenerator.mode">
                  <a-radio-button value="append">追加到现有步骤</a-radio-button>
                  <a-radio-button value="replace">覆盖现有步骤</a-radio-button>
                </a-radio-group>
              </a-form-item>
            </a-form>
            <div class="kv-title">
              <h4>生成结果</h4>
              <a-tag>{{ aiStepGenerator.generatedSteps.length }} 步</a-tag>
            </div>
            <a-table :pagination="false" size="small" :data-source="aiStepGenerator.generatedSteps" :row-key="(row: UiStepRow) => row.id" :scroll="{ x: 820, y: 260 }">
              <a-table-column title="#" width="56"><template #default="{ index }">{{ index + 1 }}</template></a-table-column>
              <a-table-column title="动作" width="110"><template #default="{ record: row }">{{ uiActionText(row.action) }}</template></a-table-column>
              <a-table-column title="定位" width="110"><template #default="{ record: row }">{{ uiLocatorText(row.locator_type) }}</template></a-table-column>
              <a-table-column title="目标"><template #default="{ record: row }"><span class="wrap-text">{{ row.target || '-' }}</span></template></a-table-column>
              <a-table-column title="值/期望" width="170"><template #default="{ record: row }"><span class="wrap-text">{{ row.value || '-' }}</span></template></a-table-column>
              <a-table-column title="说明" width="180"><template #default="{ record: row }">{{ row.description || '-' }}</template></a-table-column>
            </a-table>
            <template #footer>
              <a-button @click="resetAiStepGenerator">取消</a-button>
              <a-button :loading="aiStepGenerator.loading" @click="generateUiStepsFromPrompt">生成步骤</a-button>
              <a-button type="primary" :disabled="!aiStepGenerator.generatedSteps.length" @click="applyGeneratedUiSteps">应用步骤</a-button>
            </template>
          </a-modal>

          <a-modal
            v-model:open="uiPickerDialogVisible"
            :title="uiPicker.targetRow ? '远程元素拾取' : '录制添加步骤'"
            :width="uiPicker.targetRow ? 1180 : 'min(1480px, calc(100vw - 32px))'"
            :wrap-class-name="uiPicker.targetRow ? '' : 'ui-recorder-modal-fullscreen'"
            @cancel="closeUiPicker"
          >
            <a-alert
              class="compact-alert"
              type="info"
              show-icon
              :message="uiPicker.targetRow ? '远程浏览器运行在服务器中。选择“操作”可点击页面并输入文本，选择“拾取”后点击目标元素会生成 XPath 并回填当前步骤。' : '远程浏览器运行在服务器中。先选择录制动作并点击目标元素，确认无误后再添加到步骤列表。'"
            />
            <div class="remote-browser-toolbar">
              <a-radio-group v-model:value="uiPicker.mode" button-style="solid">
                <a-radio-button value="operate">操作</a-radio-button>
                <a-radio-button value="pick">{{ uiPicker.targetRow ? '拾取' : '录制' }}</a-radio-button>
              </a-radio-group>
              <a-select v-if="!uiPicker.targetRow" v-model:value="uiPicker.recordAction" :popup-match-select-width="false" popup-class-name="ui-action-dropdown" @change="disableUiRecordActionAuto">
                <a-select-option value="click">点击</a-select-option>
                <a-select-option value="dblclick">双击</a-select-option>
                <a-select-option value="fill">输入</a-select-option>
                <a-select-option value="select">选择</a-select-option>
                <a-select-option value="assert_visible">断言元素</a-select-option>
                <a-select-option value="assert_text">断言文本</a-select-option>
              </a-select>
              <a-tag v-if="!uiPicker.targetRow && uiPicker.recordActionAuto" color="processing">自动判断</a-tag>
              <a-select
                v-if="!uiPicker.targetRow && uiPicker.recordAction === 'select' && uiPickerSelectOptions.length"
                v-model:value="uiPicker.inputText"
                show-search
                :popup-match-select-width="false"
                popup-class-name="ui-action-dropdown"
                placeholder="请选择下拉项"
                @change="handleUiPickerSelectChange"
              >
                <a-select-option v-for="option in uiPickerSelectOptions" :key="option.key" :value="option.value">{{ uiPickerOptionLabel(option) }}</a-select-option>
              </a-select>
              <a-input v-else v-model:value="uiPicker.inputText" :placeholder="uiPicker.targetRow ? '可输入 VIN${random.string(14)} 这类动态值' : '输入步骤的值或期望文本'" @input="refreshAutoUiRecordAction" @keyup.enter="typeUiPickerText" />
              <a-button v-if="!uiPicker.targetRow && uiPicker.recordAction === 'select'" :disabled="!uiPicker.inputText.trim()" @click="applyUiPickerSelect">应用选择</a-button>
              <a-button v-if="!uiPicker.targetRow" type="primary" :disabled="!canAppendRecordedUiStep" @click="confirmAppendRecordedUiStep">添加当前步骤</a-button>
              <a-button @click="typeUiPickerText">输入</a-button>
              <a-button @click="pressUiPickerKey('Backspace')">Backspace</a-button>
              <a-button @click="pressUiPickerKey('Delete')">Delete</a-button>
              <a-button @click="pressUiPickerKey('Enter')">Enter</a-button>
              <a-button v-if="!uiPicker.targetRow" @click="appendUiPickerUtilityStep('wait')">添加等待</a-button>
              <a-button v-if="!uiPicker.targetRow" @click="appendUiPickerUtilityStep('screenshot')">添加截图</a-button>
              <a-button @click="refreshUiPickerScreenshot">刷新截图</a-button>
              <span class="ui-recorder-zoom">
                <a-button @click="changeUiPickerZoom(-10)">-</a-button>
                <a-button @click="resetUiPickerZoom">{{ uiPicker.zoomPercent }}%</a-button>
                <a-button @click="changeUiPickerZoom(10)">+</a-button>
              </span>
            </div>
            <div class="remote-browser-frame" @wheel.ctrl.prevent="handleUiPickerZoomWheel">
              <a-spin v-if="uiPicker.loading" />
              <img
                v-if="uiPicker.screenshotUrl"
                :src="uiPicker.screenshotUrl"
                alt="远程浏览器截图"
                :style="uiPickerImageStyle"
                @click="handleUiPickerImageClick"
              />
              <a-empty v-else description="等待远程浏览器截图" />
            </div>
            <a-descriptions bordered size="small" :column="1">
              <a-descriptions-item label="状态">{{ uiPicker.statusText }}</a-descriptions-item>
              <a-descriptions-item label="提示">{{ uiPicker.message || '-' }}</a-descriptions-item>
              <a-descriptions-item label="XPath"><span class="wrap-text">{{ uiPicker.xpath || '-' }}</span></a-descriptions-item>
              <a-descriptions-item label="元素">{{ uiPicker.summaryText || '-' }}</a-descriptions-item>
            </a-descriptions>
            <div v-if="!uiPicker.targetRow" class="recorded-steps-panel">
              <div class="kv-title">
                <h4>当前步骤</h4>
                <a-tag>{{ uiPickerSteps.length }} 步</a-tag>
              </div>
              <a-table :pagination="false" size="small" :data-source="uiPickerSteps" :row-key="(row: UiStepRow) => row.id" :scroll="{ x: 900, y: 220 }">
                <a-table-column title="#" width="56"><template #default="{ index }">{{ index + 1 }}</template></a-table-column>
                <a-table-column title="动作" width="110"><template #default="{ record: row }">{{ uiActionText(row.action) }}</template></a-table-column>
                <a-table-column title="目标" width="300"><template #default="{ record: row }"><span class="wrap-text">{{ row.target || '-' }}</span></template></a-table-column>
                <a-table-column title="值/期望" width="180"><template #default="{ record: row }"><span class="wrap-text">{{ row.value || '-' }}</span></template></a-table-column>
                <a-table-column title="说明"><template #default="{ record: row }">{{ row.description || '-' }}</template></a-table-column>
                <a-table-column title="操作" width="90"><template #default="{ index }"><a-button size="small" danger @click="removeUiPickerStep(index)">删除</a-button></template></a-table-column>
              </a-table>
            </div>
            <template #footer>
              <a-button @click="closeUiPicker">关闭会话</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="uiExecutionDetailVisible" title="UI执行详情" width="1040px">
            <a-alert
              v-if="currentUiExecutionError"
              class="modal-alert"
              type="error"
              show-icon
              :message="currentUiExecutionError"
            />
            <a-descriptions bordered size="small" :column="2">
              <a-descriptions-item label="状态"><a-tag :color="executionStatusColor(uiExecutionDetail.task?.status)">{{ executionStatusText(uiExecutionDetail.task?.status) }}</a-tag></a-descriptions-item>
              <a-descriptions-item label="用例">{{ uiExecutionDetail.task?.target_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="项目">{{ uiExecutionDetail.task?.project_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="环境">{{ uiExecutionDetail.task?.environment_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="执行人">{{ uiExecutionDetail.task?.executor_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="执行时间">{{ uiExecutionDetailTime }}</a-descriptions-item>
              <a-descriptions-item label="测试模式">{{ uiExecutionModeText(uiExecutionDetail.results?.[0]?.request_snapshot?.mode) }}</a-descriptions-item>
              <a-descriptions-item label="Token消耗">{{ uiTokenUsageText(uiExecutionDetail.results?.[0]?.response_snapshot?.token_usage, uiExecutionDetail.results?.[0]?.request_snapshot?.mode) }}</a-descriptions-item>
            </a-descriptions>
            <div v-for="result in uiExecutionDetail.results" :key="result.id" class="execution-result-expand log-detail-block">
              <template v-if="result.request_snapshot?.mode === 'ai'">
                <strong>测试目标</strong><pre>{{ result.request_snapshot?.test_goal || '-' }}</pre>
                <strong>测试数据</strong><pre>{{ formatJson(result.request_snapshot?.test_data || {}) }}</pre>
                <strong>期望结果</strong><pre>{{ result.request_snapshot?.assertion_goal || '-' }}</pre>
              </template>
              <a-table class="ui-detail-step-table" :pagination="false" size="small" :data-source="uiResultSteps(result)" :row-key="(row: any, index: number) => `${row.index || index}-${row.action || ''}`" :scroll="{ x: 980 }">
                <a-table-column title="步骤" width="70"><template #default="{ record: row, index }">{{ row.index || index + 1 }}</template></a-table-column>
                <a-table-column title="动作" width="110"><template #default="{ record: row }">{{ uiActionText(row.action) }}</template></a-table-column>
                <a-table-column title="定位方式" width="110"><template #default="{ record: row }">{{ uiLocatorText(row.locator_type) }}</template></a-table-column>
                <a-table-column title="目标元素/地址" width="260"><template #default="{ record: row }"><span class="wrap-text">{{ row.target || row.ref || '-' }}</span></template></a-table-column>
                <a-table-column title="值/期望" width="180"><template #default="{ record: row }"><span class="wrap-text">{{ row.value || row.expected || '-' }}</span></template></a-table-column>
                <a-table-column title="状态" width="90"><template #default="{ record: row }"><a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag></template></a-table-column>
                <a-table-column title="说明"><template #default="{ record: row }"><span class="wrap-text">{{ uiStepMessage(row) }}</span></template></a-table-column>
              </a-table>
              <strong>截图</strong>
              <div class="ui-screenshot-list">
                <a-empty v-if="!(result.response_snapshot?.screenshots || []).length" description="等待页面截图" :image-style="{ width: '44px', height: '44px' }" />
                <figure v-for="shot in result.response_snapshot?.screenshots || []" :key="shot.path" class="ui-screenshot-card">
                  <figcaption>步骤 {{ shot.step_index || '-' }} · {{ shot.type || 'screenshot' }}</figcaption>
                  <a-image :src="uiArtifactUrl(shot.path)" :width="220" />
                </figure>
              </div>
              <strong>断言结果</strong><pre>{{ formatJson(result.assertion_results || []) }}</pre>
              <template v-if="result.response_snapshot?.error_analysis">
                <strong>AI分析</strong><pre>{{ result.response_snapshot.error_analysis }}</pre>
              </template>
              <strong>错误信息</strong><pre>{{ uiResultErrorMessage(result) || '-' }}</pre>
            </div>
            <template #footer>
              <a-button :disabled="!uiExecutionDetail.task?.report_html" @click="exportUiExecutionReport">导出报告</a-button>
              <a-button v-if="hasAiExecutionResult()" @click="solidifyUiExecution">固化为高级步骤</a-button>
              <a-button v-if="uiExecutionCanStop(uiExecutionDetail.task?.status)" danger @click="stopUiExecutionFromDetail">停止任务</a-button>
              <a-button type="primary" @click="uiExecutionDetailVisible = false">关闭</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="aiSettingDialogVisible" title="AI配置" width="960px">
            <div class="ai-setting-layout">
              <div class="ai-setting-list">
                <div class="kv-title">
                  <h4>配置列表</h4>
                  <a-button size="small" @click="resetAiSettingForm">新增配置</a-button>
                </div>
                <a-table :pagination="false" size="small" :data-source="aiSettings" :row-key="(row: any) => row.id" :scroll="{ y: 300 }">
                  <a-table-column title="名称" data-index="name" />
                  <a-table-column title="状态" width="76"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'default'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
                  <a-table-column title="默认" width="76"><template #default="{ record: row }"><a-tag v-if="row.is_default" color="processing">默认</a-tag><span v-else>-</span></template></a-table-column>
                  <a-table-column title="操作" width="190" fixed="right">
                    <template #default="{ record: row }">
                      <div class="table-actions">
                        <a-button size="small" @click="editAiSetting(row)">编辑</a-button>
                        <a-button size="small" :disabled="row.is_default" @click="setDefaultAiSetting(row)">设默认</a-button>
                        <a-button size="small" danger @click="deleteAiSetting(row)">删除</a-button>
                      </div>
                    </template>
                  </a-table-column>
                </a-table>
              </div>
              <a-form layout="vertical" class="ai-setting-form" @submit.prevent="saveAiSetting">
              <a-form-item label="配置名称"><a-input v-model:value="aiSettingForm.name" placeholder="例如 DeepSeek、Qwen、内网模型" /></a-form-item>
              <a-form-item label="模型服务地址"><a-input v-model:value="aiSettingForm.provider_url" placeholder="https://模型网关地址/v1" /></a-form-item>
              <a-form-item label="模型名称"><a-input v-model:value="aiSettingForm.model_name" placeholder="例如 ui-agent" /></a-form-item>
              <a-form-item label="API Key"><a-input-password v-model:value="aiSettingForm.api_key" placeholder="留空则不修改已有 Key" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="aiSettingForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="默认配置"><a-switch v-model:checked="aiSettingForm.is_default" checked-children="默认" un-checked-children="普通" /></a-form-item>
              <a-form-item label="说明"><a-textarea v-model:value="aiSettingForm.description" :rows="3" placeholder="用于后续 AI 生成 UI 测试步骤和辅助识别元素" /></a-form-item>
              </a-form>
            </div>
            <template #footer>
              <a-button @click="aiSettingDialogVisible = false">取消</a-button>
              <a-button :loading="aiSettingTesting" @click="testAiSetting">测试连接</a-button>
              <a-button type="primary" @click="saveAiSetting">{{ aiSettingForm.id ? '保存配置' : '新增配置' }}</a-button>
            </template>
          </a-modal>

        <section v-if="activeUiCaseEditor" class="api-editor-page ui-case-editor-page">
          <div class="toolbar">
            <h2>{{ activeUiCaseEditor.label }}</h2>
            <div class="toolbar-actions">
              <a-button @click="closeUiCaseEditorFromPage">取消</a-button>
              <a-button type="primary" @click="saveUiCaseEditor">保存UI用例</a-button>
            </div>
          </div>

          <div class="editor-section">
            <h3>基础信息</h3>
            <a-form layout="vertical" class="form-grid" @submit.prevent="saveUiCaseEditor">
              <a-form-item label="项目">
                <a-select v-model:value="activeUiCaseEditor.form.project_id" placeholder="请选择项目" @change="changeUiCaseEditorProject(activeUiCaseEditor.form)">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境">
                <a-select v-model:value="activeUiCaseEditor.form.environment_id" placeholder="请先选择项目" :disabled="!activeUiCaseEditor.form.project_id">
                  <a-select-option v-for="e in uiCaseEditorEnvironments(activeUiCaseEditor.form)" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="用例名称"><a-input v-model:value="activeUiCaseEditor.form.name" placeholder="请输入UI用例名称" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="activeUiCaseEditor.form.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器"><a-select v-model:value="activeUiCaseEditor.form.browser_channel"><a-select-option value="chromium">Playwright Chromium</a-select-option><a-select-option value="chrome">本机 Chrome</a-select-option><a-select-option value="msedge">本机 Edge</a-select-option></a-select></a-form-item>
              <a-form-item label="浏览器模式"><a-select v-model:value="activeUiCaseEditor.form.headless"><a-select-option :value="true">无头模式</a-select-option><a-select-option :value="false">有头模式</a-select-option></a-select></a-form-item>
              <a-form-item label="页面等待"><a-select v-model:value="activeUiCaseEditor.form.wait_until"><a-select-option value="networkidle">网络空闲</a-select-option><a-select-option value="load">页面加载完成</a-select-option><a-select-option value="domcontentloaded">DOM加载完成</a-select-option></a-select></a-form-item>
              <a-form-item label="额外等待(ms)"><a-input-number v-model:value="activeUiCaseEditor.form.wait_after_load_ms" :min="0" :max="60000" :step="500" style="width: 100%" /></a-form-item>
              <a-form-item label="目标地址" class="wide"><a-input v-model:value="activeUiCaseEditor.form.start_url" placeholder="/login 或完整 URL" /></a-form-item>
              <a-form-item label="用例模式" class="wide">
                <a-radio-group v-model:value="activeUiCaseEditor.form.execution_mode">
                  <a-radio-button value="ai">AI模式</a-radio-button>
                  <a-radio-button value="advanced">高级模式</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <template v-if="activeUiCaseEditor.form.execution_mode === 'ai'">
                <a-form-item label="测试目标" class="wide"><a-textarea v-model:value="activeUiCaseEditor.form.test_goal" :rows="4" placeholder="例如：登录系统后进入合同列表，按合同编号查询详情，并确认页面展示合同信息" /></a-form-item>
                <a-form-item label="测试数据" class="wide"><a-textarea v-model:value="activeUiCaseEditor.form.test_data_text" :rows="5" placeholder="{&#10;  &quot;用户名&quot;: &quot;test&quot;,&#10;  &quot;密码&quot;: &quot;123456&quot;,&#10;  &quot;合同编号&quot;: &quot;HT001&quot;&#10;}" /></a-form-item>
                <a-form-item label="期望结果" class="wide"><a-textarea v-model:value="activeUiCaseEditor.form.assertion_goal" :rows="3" placeholder="例如：页面出现合同编号，且状态为正常" /></a-form-item>
                <a-form-item label="最大步骤数"><a-input-number v-model:value="activeUiCaseEditor.form.max_steps" :min="1" :max="100" style="width: 100%" /></a-form-item>
                <a-form-item label="单步超时(ms)"><a-input-number v-model:value="activeUiCaseEditor.form.step_timeout_ms" :min="1000" :max="120000" :step="1000" style="width: 100%" /></a-form-item>
                <a-form-item label="允许AI操作"><a-switch v-model:checked="activeUiCaseEditor.form.allow_ai_actions" checked-children="允许" un-checked-children="只观察" /></a-form-item>
                <a-alert class="wide compact-alert" type="info" show-icon message="AI模式会在受控浏览器中观察当前页面，并在点击、输入、选择、断言等安全动作中选择下一步；每一步都会保存原因、截图和执行结果。" />
              </template>
              <a-form-item label="描述" class="wide"><a-textarea v-model:value="activeUiCaseEditor.form.description" :rows="2" placeholder="请输入用例说明" /></a-form-item>
            </a-form>
          </div>

          <div v-if="activeUiCaseEditor.form.execution_mode === 'advanced'" class="editor-section">
            <div class="kv-title">
              <h4>测试步骤</h4>
              <div class="toolbar-actions">
                <a-button size="small" @click="openAiStepDialog(activeUiCaseEditor.form)">自然语言生成</a-button>
                <a-button size="small" @click="startUiStepRecorder(activeUiCaseEditor.form)">录制添加步骤</a-button>
                <a-button size="small" @click="addUiStep(activeUiCaseEditor.form)">添加步骤</a-button>
              </div>
            </div>
            <a-alert class="compact-alert" type="info" show-icon message="定位方式选择“AI描述”时，目标元素可填写自然语言，例如：点击登录按钮、填写用户名输入框；执行时会自动转换为可执行定位器。" />
            <a-table
              class="ui-step-table"
              :pagination="false"
              :data-source="activeUiCaseEditor.form.steps"
              :row-key="(row: UiStepRow) => row.id"
              :scroll="{ x: 1180 }"
              :custom-row="activeUiStepRowProps"
            >
              <a-table-column title="步骤ID" width="96">
                <template #default="{ index }">
                  <span class="ui-step-id">
                    <span
                      class="drag-handle"
                      draggable="true"
                      title="拖动调整步骤顺序"
                      @dragstart="startUiStepDrag(activeUiCaseEditor.form, index, $event)"
                      @dragend="resetUiStepDrag"
                    >⋮⋮</span>
                    {{ index + 1 }}
                  </span>
                </template>
              </a-table-column>
              <a-table-column title="动作" width="170"><template #default="{ record: row }"><a-select v-model:value="row.action" :popup-match-select-width="false" popup-class-name="ui-action-dropdown"><a-select-option value="goto">打开页面</a-select-option><a-select-option value="click">点击</a-select-option><a-select-option value="dblclick">双击</a-select-option><a-select-option value="fill">输入</a-select-option><a-select-option value="select">选择</a-select-option><a-select-option value="wait">等待</a-select-option><a-select-option value="assert_text">断言文本</a-select-option><a-select-option value="assert_visible">断言元素</a-select-option><a-select-option value="screenshot">截图</a-select-option></a-select></template></a-table-column>
              <a-table-column title="定位方式" width="170"><template #default="{ record: row }"><a-select v-model:value="row.locator_type" :popup-match-select-width="false" popup-class-name="ui-locator-dropdown"><a-select-option value="css">CSS</a-select-option><a-select-option value="xpath">XPath</a-select-option><a-select-option value="text">文本</a-select-option><a-select-option value="placeholder">占位符</a-select-option><a-select-option value="role">按钮文字</a-select-option><a-select-option value="ai">AI描述</a-select-option></a-select></template></a-table-column>
              <a-table-column title="目标元素/地址" width="260"><template #default="{ record: row }"><a-input v-model:value="row.target" placeholder="CSS、XPath、文本，或写：点击登录按钮" /></template></a-table-column>
              <a-table-column title="值/期望" width="220"><template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="如 VIN${random.string(14)}，或等待毫秒" /></template></a-table-column>
              <a-table-column title="说明" width="220"><template #default="{ record: row }"><a-input v-model:value="row.description" placeholder="步骤说明" /></template></a-table-column>
              <a-table-column title="操作" width="230" fixed="right"><template #default="{ record: row, index }"><div class="table-actions"><a-button size="small" @click="startUiElementPicker(activeUiCaseEditor.form, row)">拾取</a-button><a-button size="small" @click="moveUiStep(activeUiCaseEditor.form, index, -1)">上移</a-button><a-button size="small" @click="moveUiStep(activeUiCaseEditor.form, index, 1)">下移</a-button><a-button size="small" danger @click="removeUiStep(activeUiCaseEditor.form, index)">删除</a-button></div></template></a-table-column>
            </a-table>
          </div>

          <div class="plan-editor-footer">
            <span>保存成功后会自动关闭当前页签</span>
            <div class="toolbar-actions">
              <a-button @click="closeUiCaseEditorFromPage">取消</a-button>
              <a-button type="primary" @click="saveUiCaseEditor">保存UI用例</a-button>
            </div>
          </div>
        </section>

        <section v-if="activeApiEditor" class="api-editor-page">
          <div class="toolbar">
            <h2>{{ activeApiEditor.label }}</h2>
            <div class="toolbar-actions">
              <a-button @click="closeApiEditorFromPage(activeApiEditor)">关闭</a-button>
              <a-button type="primary" @click="saveApiEditor(activeApiEditor, true)">保存</a-button>
            </div>
          </div>

          <div class="editor-section">
            <h3>基础信息</h3>
            <a-form layout="vertical" class="form-grid">
              <a-form-item label="项目">
                <a-select
                  v-model:value="activeApiEditor.project_id"
                  placeholder="请选择项目"
                  @change="changeApiEditorProject(activeApiEditor)"
                >
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="名称">
                <a-input v-model:value="activeApiEditor.name" placeholder="请输入接口名称" @input="markApiEditorDirty(activeApiEditor)" />
              </a-form-item>
              <a-form-item label="接口描述" class="wide">
                <a-textarea v-model:value="activeApiEditor.description" :rows="3" placeholder="请输入接口描述" @input="markApiEditorDirty(activeApiEditor)" />
              </a-form-item>
            </a-form>
          </div>

          <div class="editor-section">
            <h3>接口信息</h3>
            <div class="request-line">
              <a-select v-model:value="activeApiEditor.method" placeholder="方法" class="method-select" @change="markApiEditorDirty(activeApiEditor)">
                <a-select-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-select-option>
              </a-select>
              <a-input v-model:value="activeApiEditor.path" placeholder="请输入接口路径 URL，例如 /users" @input="changeApiEditorPath(activeApiEditor)" />
            </div>

            <a-tabs v-model:active-key="activeApiEditor.activePanel" class="api-info-tabs">
              <a-tab-pane tab="URL参数" key="query">
                <div class="kv-title">
                  <h4>URL参数</h4>
                  <a-button size="small" @click="addApiEditorRow(activeApiEditor.queryRows)">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="activeApiEditor.queryRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="key" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeApiEditorRow(activeApiEditor.queryRows, $index, activeApiEditor)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </a-tab-pane>

              <a-tab-pane tab="请求头Header" key="headers">
                <div class="kv-title">
                  <h4>请求头Header</h4>
                  <a-button size="small" @click="addApiEditorRow(activeApiEditor.headerRows)">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="activeApiEditor.headerRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="Authorization / Content-Type" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeApiEditorRow(activeApiEditor.headerRows, $index, activeApiEditor)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </a-tab-pane>

              <a-tab-pane tab="鉴权" key="auth">
                <div class="auth-panel">
                  <div class="auth-sidebar">
                    <a-form layout="vertical">
                      <a-form-item label="鉴权类型">
                        <a-select v-model:value="activeApiEditor.auth.type" @change="changeApiAuthType(activeApiEditor)">
                          <a-select-option value="none">无鉴权</a-select-option>
                          <a-select-option value="bearer">Bearer Token</a-select-option>
                          <a-select-option value="basic">Basic 鉴权</a-select-option>
                          <a-select-option value="api_key">API Key</a-select-option>
                          <a-select-option value="oauth2_client_credentials">OAuth 2.0</a-select-option>
                        </a-select>
                      </a-form-item>
                      <a-form-item label="鉴权数据添加到">
                        <a-select v-model:value="activeApiEditor.auth.addTo" @change="markApiEditorDirty(activeApiEditor)">
                          <a-select-option value="headers">请求头 Header</a-select-option>
                          <a-select-option value="query">URL 参数</a-select-option>
                        </a-select>
                      </a-form-item>
                    </a-form>
                  </div>
                  <div class="auth-main">
                    <a-empty v-if="activeApiEditor.auth.type === 'none'" description="当前接口不启用鉴权" />
                    <a-form v-else layout="vertical" class="auth-form-grid">
                      <template v-if="activeApiEditor.auth.type === 'bearer'">
                        <a-form-item label="请求头名称">
                          <a-input v-model:value="activeApiEditor.auth.headerName" placeholder="Authorization" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="请求头前缀">
                          <a-input v-model:value="activeApiEditor.auth.headerPrefix" placeholder="Bearer" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Token" class="wide">
                          <a-input-password v-model:value="activeApiEditor.auth.token" placeholder="${token} / token" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else-if="activeApiEditor.auth.type === 'basic'">
                        <a-form-item label="用户名">
                          <a-input v-model:value="activeApiEditor.auth.username" placeholder="${username}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="密码">
                          <a-input-password v-model:value="activeApiEditor.auth.password" placeholder="${password}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else-if="activeApiEditor.auth.type === 'api_key'">
                        <a-form-item label="Key">
                          <a-input v-model:value="activeApiEditor.auth.apiKeyName" placeholder="x-api-key" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Value">
                          <a-input-password v-model:value="activeApiEditor.auth.apiKeyValue" placeholder="${api_key}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else>
                        <div class="wide auth-token-box">
                          <h4>当前 Token</h4>
                          <a-form-item label="Access Token">
                            <a-input v-model:value="activeApiEditor.auth.currentToken" readonly placeholder="获取后显示 Access Token" />
                          </a-form-item>
                          <a-form-item label="请求头前缀">
                            <a-input v-model:value="activeApiEditor.auth.headerPrefix" placeholder="Bearer" @input="markApiEditorDirty(activeApiEditor)" />
                          </a-form-item>
                        </div>
                        <div class="wide auth-section-title">
                          <h4>配置新 Token</h4>
                          <a-button size="small" @click="generateApiAuthUrls(activeApiEditor, true)">一键生成 URL/Scope</a-button>
                        </div>
                        <a-form-item label="授权模式">
                          <a-input v-model:value="activeApiEditor.auth.grantType" placeholder="client_credentials / ${grant_type}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Access Token URL" class="wide">
                          <a-input v-model:value="activeApiEditor.auth.tokenUrl" placeholder="环境地址 + /OAuth/Oauth/Token" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Client ID">
                          <a-input v-model:value="activeApiEditor.auth.clientId" placeholder="KSTAPI / ${client_id}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Client Secret">
                          <a-input-password v-model:value="activeApiEditor.auth.clientSecret" placeholder="1234 / ${client_secret}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Scope" class="wide">
                          <a-input v-model:value="activeApiEditor.auth.scope" placeholder="默认当前环境地址 + 接口路径" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="客户端认证方式" class="wide">
                          <a-select v-model:value="activeApiEditor.auth.clientAuthentication" @change="markApiEditorDirty(activeApiEditor)">
                            <a-select-option value="body">在请求体中发送 Client ID/Secret</a-select-option>
                            <a-select-option value="basic">通过 Basic Auth 请求头发送</a-select-option>
                          </a-select>
                        </a-form-item>
                        <a-form-item class="wide">
                          <a-checkbox v-model:checked="activeApiEditor.auth.verifyTls" @change="markApiEditorDirty(activeApiEditor)">校验 SSL 证书</a-checkbox>
                          <p class="form-help-text">如果和 Postman 关闭 SSL 校验后才能获取 Token，可取消勾选。</p>
                        </a-form-item>
                        <div class="wide">
                          <a-button type="primary" :loading="activeApiEditor.auth.loading" @click="getApiEditorAccessToken(activeApiEditor)">获取 Access Token</a-button>
                        </div>
                      </template>
                    </a-form>
                  </div>
                </div>
              </a-tab-pane>

              <a-tab-pane tab="请求Body" key="body">
                <div class="body-format-row">
                  <span>Body格式</span>
                  <a-radio-group v-model:value="activeApiEditor.bodyFormat" @change="changeApiEditorBodyFormat(activeApiEditor)">
                    <a-radio-button value="json">json</a-radio-button>
                    <a-radio-button value="xml">xml</a-radio-button>
                    <a-radio-button value="x-www-form-data">x-www-form-data</a-radio-button>
                  </a-radio-group>
                </div>
                <div class="body-editor-head">
                  <span>请求体模板</span>
                  <a-button size="small" @click="formatApiBodyTemplate(activeApiEditor)">格式化</a-button>
                </div>
                <BodyCodeEditor
                  v-model="activeApiEditor.bodyTemplate"
                  :language="activeApiEditor.bodyFormat"
                  :placeholder="apiBodyTemplatePlaceholder(activeApiEditor)"
                  min-height="240px"
                  @update:model-value="markApiEditorDirty(activeApiEditor)"
                />
                <p class="form-help-text">新建用例选择该接口时会自动带入模板；模板中可使用 ${变量名}。</p>
              </a-tab-pane>
              <a-tab-pane tab="Pre-script" key="pre-script">
                <a-textarea
                  v-model:value="activeApiEditor.preScript"
                  :rows="14"
                  class="pre-script-input"
                  placeholder="pm.environment.set('timestamp', Date.now());&#10;pm.environment.set('sign', CryptoJS.MD5(pm.environment.get('timestamp')).toString());"
                  @input="markApiEditorDirty(activeApiEditor)"
                />
                <p class="pre-script-hint">
                  支持 pm.environment.get/set、Date、Math、JSON、CryptoJS.MD5/SHA256 和 console.log/info/warn；不支持 require、网络请求、文件或数据库访问。
                </p>
              </a-tab-pane>
              <a-tab-pane tab="加密配置" key="encryption">
                <a-form layout="vertical">
                  <a-form-item label="启用加密配置">
                    <a-switch v-model:checked="activeApiEditor.encryption.enabled" @change="markApiEditorDirty(activeApiEditor)" />
                  </a-form-item>
                  <template v-if="activeApiEditor.encryption.enabled">
                    <a-form-item label="加密方式">
                      <a-select v-model:value="activeApiEditor.encryption.mode" @change="markApiEditorDirty(activeApiEditor)">
                        <a-select-option value="rsa_aes_sm3">RSA-AES-SM3</a-select-option>
                      </a-select>
                    </a-form-item>
                    <a-form-item label="处理方式">
                      <a-checkbox v-model:checked="activeApiEditor.encryption.encryptRequest" @change="markApiEditorDirty(activeApiEditor)">请求 Body 加密</a-checkbox>
                      <a-checkbox v-model:checked="activeApiEditor.encryption.decryptResponse" @change="markApiEditorDirty(activeApiEditor)">响应 Body 解密</a-checkbox>
                    </a-form-item>
                    <p class="pre-script-hint">平台使用服务器预置的固定 RSA 密钥，无需上传 PEM 文件。</p>
                  </template>
                </a-form>
              </a-tab-pane>
              <a-tab-pane tab="SM3签名" key="sm3-signature">
                <a-form layout="vertical" class="sm3-signature-form">
                  <a-form-item label="启用SM3签名">
                    <a-switch v-model:checked="activeApiEditor.encryption.sm3Signature" @change="markApiEditorDirty(activeApiEditor)" />
                  </a-form-item>
                  <template v-if="activeApiEditor.encryption.sm3Signature">
                    <p class="pre-script-hint">执行时会在变量替换和鉴权处理后，使用最终请求体原文计算 SM3，并以大写 Hex 追加到请求体尾部。</p>
                    <p class="pre-script-hint">当前第一版仅支持 XML 请求体；请求模板和用例 Body 不会被写入签名，签名只在实际发送时自动追加。</p>
                  </template>
                </a-form>
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>

        <section v-if="active === 'cases'" class="page-view">
          <div class="toolbar"><h2>用例管理</h2><a-button type="primary" @click="openCreateCasePage"><template #icon><PlusOutlined /></template>新增用例</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="caseSearch.project_id" placeholder="请选择项目" allow-clear @change="changeCaseSearchProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="接口">
              <a-select v-model:value="caseSearch.api_id" placeholder="请先选择项目" allow-clear :disabled="!caseSearch.project_id">
                <a-select-option v-for="a in caseSearchApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchCases">搜索</a-button>
              <a-button @click="resetCaseSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="caseList">
            <a-table-column title="编号" width="80">
              <template #default="{ index }">{{ caseSerialNumber(index) }}</template>
            </a-table-column>
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="接口"><template #default="{ record: row }"><TableText :value="row.api_name" /></template></a-table-column>
            <a-table-column title="用例名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="操作" width="330" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openCaseDetailDialog(row)">查看</a-button>
                  <a-button size="small" @click="openEditCasePage(row)">编辑</a-button>
                  <a-button size="small" @click="copyCase(row)">复制</a-button>
                  <a-button size="small" danger @click="deleteCase(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="casePagination.page"
              :page-size="casePagination.pageSize"
              :total="casePagination.total"
              @change="changeCasePage"
            />
          </div>
        </section>

        <section v-if="active === 'case-create' || active.startsWith('case-edit-')">
          <div class="toolbar">
            <h2>{{ caseForm.id ? '编辑用例' : '新增用例' }}</h2>
            <div class="toolbar-actions">
              <a-button @click="closeCaseEditorPage">关闭</a-button>
              <a-button type="primary" @click="saveCase">保存</a-button>
            </div>
          </div>
          <a-form layout="vertical" class="form-grid">
            <a-form-item label="项目">
              <a-select v-model:value="caseForm.project_id" placeholder="请选择项目" @change="changeCaseFormProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="接口">
              <a-select v-model:value="caseForm.api_id" placeholder="请先选择项目" :disabled="!caseForm.project_id" @change="changeCaseFormApi">
                <a-select-option v-for="a in caseFormApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input v-model:value="caseForm.name" placeholder="请输入用例名称" />
            </a-form-item>
            <a-form-item label="用例描述" class="wide">
              <a-textarea v-model:value="caseForm.description" :rows="3" placeholder="请输入用例描述" class="case-description-input" />
            </a-form-item>
            <a-form-item label="Body" class="wide">
              <div class="body-editor-head">
                <span>当前格式：{{ caseBodyFormatLabel }}{{ caseBodySm3Hint }}</span>
                <div class="body-editor-actions">
                  <a-button size="small" @click="reuseCaseBodyTemplate">复用请求体</a-button>
                  <a-button size="small" @click="formatCaseBody">格式化</a-button>
                </div>
              </div>
              <BodyCodeEditor
                v-model="caseForm.bodyText"
                :language="caseForm.bodyFormat"
                :placeholder="caseBodyPlaceholder"
                min-height="220px"
              />
              <p class="form-help-text">{{ caseBodyHelpText }} 可直接引用上游提取变量，例如 ${token}、${userId}，测试计划按队列顺序执行时会自动替换。</p>
            </a-form-item>
            <div class="wide">
              <div class="kv-title">
                <h4>响应提取 / 参数关联</h4>
                <a-button size="small" @click="addCaseExtractorRow">添加</a-button>
              </div>
              <a-table :pagination="false" :data-source="caseForm.extractorRows">
                <a-table-column title="提取方式" width="170">
                  <template #default="{ record: row }">
                    <a-select v-model:value="row.source">
                      <a-select-option v-for="option in extractorTypes" :key="option.value" :value="option.value">{{ option.label }}</a-select-option>
                    </a-select>
                  </template>
                </a-table-column>
                <a-table-column title="变量名" width="220">
                  <template #default="{ record: row }"><a-input v-model:value="row.name" placeholder="token" /></template>
                </a-table-column>
                <a-table-column title="提取表达式">
                  <template #default="{ record: row }">
                    <a-input v-model:value="row.path" :placeholder="caseExtractorPlaceholder(row.source)" />
                  </template>
                </a-table-column>
                <a-table-column title="操作" width="90">
                  <template #default="{ index: $index }"><a-button size="small" danger @click="removeCaseExtractorRow($index)">删除</a-button></template>
                </a-table-column>
              </a-table>
              <p class="form-help-text">提取成功后，后续用例可在 Body 中使用 ${变量名} 引用。XML 返回可用 XMLPath，例如 .//STATUS 或 /RESPONSE/STATUS。</p>
            </div>
            <div class="wide">
              <div class="kv-title">
                <h4>断言</h4>
                <a-button size="small" @click="addCaseAssertionRow">添加</a-button>
              </div>
              <a-table :pagination="false" :data-source="caseForm.assertionRows">
                <a-table-column title="断言对象" width="160">
                  <template #default="{ record: row }">
                    <a-select v-model:value="row.target" @change="changeCaseAssertionTarget(row)">
                      <a-select-option v-for="option in assertionTargets" :key="option.value" :value="option.value">{{ option.label }}</a-select-option>
                    </a-select>
                  </template>
                </a-table-column>
                <a-table-column title="断言方式" width="150">
                  <template #default="{ record: row }">
                    <a-select v-model:value="row.check" @change="syncCaseAssertionType(row)">
                      <a-select-option v-for="option in assertionCheckOptions(row.target)" :key="option.value" :value="option.value">{{ option.label }}</a-select-option>
                    </a-select>
                  </template>
                </a-table-column>
                <a-table-column title="路径/表达式">
                  <template #default="{ record: row }">
                    <a-input v-model:value="row.path" :disabled="!assertionNeedsPath(row.target)" :placeholder="assertionPathPlaceholder(row.target)" />
                  </template>
                </a-table-column>
                <a-table-column title="期望值">
                  <template #default="{ record: row }">
                    <a-input-number
                      v-if="isNumericAssertion(row.target)"
                      v-model:value="row.expected"
                      :min="0"
                      :precision="0"
                      :placeholder="assertionExpectedPlaceholder(row.target)"
                      style="width: 100%"
                    />
                    <a-input v-else v-model:value="row.expected" :disabled="['exists', 'not_empty'].includes(row.check)" :placeholder="assertionExpectedPlaceholder(row.target)" />
                  </template>
                </a-table-column>
                <a-table-column title="操作" width="90">
                  <template #default="{ index: $index }"><a-button size="small" danger @click="removeCaseAssertionRow($index)">删除</a-button></template>
                </a-table-column>
              </a-table>
            </div>
          </a-form>
        </section>

        <a-modal v-model:open="caseBodyDialogVisible" title="请求 Body" width="640px">
          <a-textarea v-model:value="caseBodyPreview" :rows="16" readonly />
          <template #footer>
            <a-button type="primary" @click="caseBodyDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <section v-if="active === 'execute'" class="plan-page">
          <div class="plan-page-header plan-workbench-header">
            <div>
              <h2>测试计划</h2>
              <p>编排回归范围，统一查看执行状态与最新结果。</p>
            </div>
              <a-button type="primary" @click="openCreatePlanPage"><template #icon><PlusOutlined /></template>新建测试计划</a-button>
          </div>
          <div class="plan-search-panel plan-filter-bar">
            <a-form class="search-form plan-search-form" layout="inline">
              <a-form-item label="计划名称">
                <a-input v-model:value="planSearch.name" placeholder="请输入计划名称" allow-clear @keyup.enter="searchPlans" />
              </a-form-item>
              <a-form-item label="项目">
                <a-select v-model:value="planSearch.project_id" placeholder="请选择项目" allow-clear @change="changePlanSearchProject">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="包含接口">
                <a-select v-model:value="planSearch.api_id" placeholder="请先选择项目" allow-clear :disabled="!planSearch.project_id">
                <a-select-option v-for="a in planSearchApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <div class="search-actions">
                <a-button type="primary" @click="searchPlans">查询</a-button>
                <a-button @click="resetPlanSearch">重置</a-button>
              </div>
            </a-form>
          </div>
          <div class="plan-table-panel plan-data-surface">
            <div class="plan-table-heading plan-list-toolbar">
              <div>
                <h3>全部计划</h3>
                <span>共 {{ planPagination.total }} 条记录</span>
              </div>
              <div class="toolbar-actions">
                <span class="plan-list-hint">点击计划名称可查看执行范围</span>
                <a-button :disabled="!selectedPlanIds.length" :loading="batchExecutingPlans" @click="executeSelectedPlans">批量执行</a-button>
              </div>
            </div>
          <a-table
            :pagination="false"
            :data-source="planList"
            row-key="id"
            :row-selection="{ selectedRowKeys: selectedPlanIds, onChange: changeSelectedPlans }"
            :scroll="{ x: 1360 }"
            class="plan-list-table"
          >
            <template #expandedRowRender="{ record: row }">
              <div class="plan-case-expand-list">
                <div class="plan-case-expand-head">
                  <span>用例名称</span>
                  <span>接口</span>
                  <span>环境</span>
                  <span>状态</span>
                  <span>操作</span>
                </div>
                <div v-for="caseRow in row.cases || []" :key="caseRow.id" class="plan-case-expand-row">
                  <span class="plan-case-expand-name">{{ caseRow.name || '-' }}</span>
                  <span class="plan-case-expand-api">{{ caseRow.api_name || '-' }}</span>
                  <span class="plan-case-expand-env">{{ caseRow.environment_name || planEnvironmentName(row, caseRow.environment_id) || '-' }}</span>
                  <span><a-tag :color="executionStatusColor(caseRow.status)">{{ executionStatusText(caseRow.status) }}</a-tag></span>
                  <span class="plan-case-expand-action">
                    <a-button size="small" @click="openCaseDetailDialog(caseRow, caseRow.environment_id || row.environment_id, row.last_execution_id)">查看</a-button>
                  </span>
                </div>
                <a-empty v-if="!(row.cases || []).length" description="暂无用例" :image-style="{ width: '48px', height: '48px' }" />
              </div>
            </template>
            <a-table-column title="计划名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="环境"><template #default="{ record: row }"><TableText :value="row.environment_name" /></template></a-table-column>
            <a-table-column title="包含接口"><template #default="{ record: row }"><TableText :value="row.api_name" /></template></a-table-column>
            <a-table-column title="状态" width="96" align="center">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.last_status)">{{ executionStatusText(row.last_status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行时间" width="150">
              <template #default="{ record: row }">{{ formatMinute(row.last_executed_at) }}</template>
            </a-table-column>
            <a-table-column title="操作" width="240" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" type="primary" @click="executePlan(row)">执行</a-button>
                  <a-button size="small" type="link" @click="openEditPlanPage(row)">编辑</a-button>
                  <a-button size="small" type="link" @click="openExecutionDetail(row)">进度</a-button>
                  <a-button size="small" type="link" danger @click="deletePlan(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="planPagination.page"
              :page-size="planPagination.pageSize"
              :total="planPagination.total"
              @change="changePlanPage"
            />
          </div>
          </div>
        </section>

        <section v-if="activePlanEditor" class="plan-editor-page">
          <div class="plan-editor-header plan-editor-titlebar">
            <div>
              <h2>{{ activePlanEditor.label }}</h2>
              <p>{{ activePlanEditor.dirty ? '存在未保存的更改' : '所有更改已保存' }}</p>
            </div>
          </div>

          <div class="plan-editor-workspace">
            <aside class="plan-editor-rail" aria-label="计划配置步骤">
              <div class="plan-editor-rail-title">配置步骤</div>
              <div class="plan-editor-step is-active"><span>01</span><div><strong>基础配置</strong><small>项目、环境与接口</small></div></div>
              <div class="plan-editor-step"><span>02</span><div><strong>选择用例</strong><small>筛选并加入执行范围</small></div></div>
              <div class="plan-editor-step"><span>03</span><div><strong>执行编排</strong><small>调整用例执行顺序</small></div></div>
            </aside>

            <div class="plan-editor-content">
              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading">
                  <div>
                    <span class="plan-section-index">01</span>
                    <h3>基础配置</h3>
                    <p>选择目标项目、执行环境和需要覆盖的接口。</p>
                  </div>
                </div>
                <a-form layout="vertical" class="form-grid">
                  <a-form-item label="项目">
                    <a-select v-model:value="activePlanEditor.project_id" placeholder="请选择项目" @change="changePlanEditorProject(activePlanEditor)">
                      <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="默认环境">
                    <a-select v-model:value="activePlanEditor.environment_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="changePlanEditorDefaultEnvironment(activePlanEditor)">
                      <a-select-option v-for="e in planEditorEnvironments(activePlanEditor)" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="接口">
                    <a-select v-model:value="activePlanEditor.api_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="changePlanEditorApi(activePlanEditor)">
                      <a-select-option v-for="a in planEditorApis(activePlanEditor)" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="测试计划名称">
                    <a-input v-model:value="activePlanEditor.name" placeholder="请输入测试计划名称" @input="markPlanEditorDirty(activePlanEditor)" />
                  </a-form-item>
                </a-form>
              </div>

              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading plan-section-heading-actions">
                  <div>
                    <span class="plan-section-index">02</span>
                    <h3>选择测试用例</h3>
                    <p>查询后勾选用例，并添加到下方执行队列。</p>
                  </div>
                  <div class="toolbar-actions">
                    <a-button @click="loadPlanCandidateCases(activePlanEditor)">刷新列表</a-button>
                    <a-button type="primary" @click="addSelectedPlanCases(activePlanEditor)">加入队列</a-button>
                  </div>
                </div>
                <a-table :pagination="false"
                  :data-source="activePlanEditor.candidateCases"
                  size="small"
                  row-key="id"
                  :row-selection="{ onChange: (_keys: any[], rows: any[]) => changePlanCandidateSelection(activePlanEditor, rows) }"
                >
                  <a-table-column title="用例名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
                  <a-table-column title="接口"><template #default="{ record: row }"><TableText :value="row.api_name" /></template></a-table-column>
                  <a-table-column title="操作" width="100">
                    <template #default="{ record: row }">
                      <a-button size="small" type="link" @click="openCaseDetailDialog(row, activePlanEditor.environment_id)">查看</a-button>
                    </template>
                  </a-table-column>
                </a-table>
              </div>

              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading">
                  <div>
                    <span class="plan-section-index">03</span>
                    <h3>执行队列</h3>
                    <p>拖动用例调整执行顺序。</p>
                  </div>
                  <span class="plan-queue-count">{{ activePlanEditor.queue.length }} 个用例</span>
                </div>
                <div class="plan-queue">
                  <div
                    v-for="(item, index) in activePlanEditor.queue"
                    :key="item.id"
                    class="plan-queue-row"
                    draggable="true"
                    @dragstart="startPlanQueueDrag(activePlanEditor, index)"
                    @dragover.prevent
                    @drop="dropPlanQueueRow(activePlanEditor, index)"
                  >
                    <span class="drag-handle">⋮⋮</span>
                    <span class="queue-name">{{ item.name }}</span>
                    <span class="queue-api">{{ item.api_name || '-' }}</span>
                    <a-select
                      v-model:value="item.environment_id"
                      size="small"
                      class="queue-environment-select"
                      placeholder="执行环境"
                      @change="markPlanEditorDirty(activePlanEditor)"
                    >
                      <a-select-option v-for="e in planEditorEnvironments(activePlanEditor)" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                    </a-select>
                    <a-button size="small" type="link" @click="openCaseDetailDialog(item, item.environment_id || activePlanEditor.environment_id)">查看</a-button>
                    <a-button size="small" type="link" danger @click="removePlanQueueCase(activePlanEditor, index)">移除</a-button>
                  </div>
                  <a-empty v-if="activePlanEditor.queue.length === 0" description="暂无用例" />
                </div>
              </div>
            </div>
          </div>
          <div class="plan-editor-footer">
            <span>{{ activePlanEditor.dirty ? '当前内容尚未保存' : '已保存' }}</span>
            <div class="toolbar-actions">
              <a-button @click="closePlanEditorFromPage(activePlanEditor)">取消</a-button>
              <a-button type="primary" @click="savePlanEditor(activePlanEditor, true)">保存测试计划</a-button>
            </div>
          </div>
        </section>

        <a-modal v-model:open="caseDetailDialogVisible" title="用例详情" width="760px">
          <div class="detail-grid">
            <strong>请求方法</strong><span>{{ caseDetail.method || '-' }}</span>
            <strong>URL</strong><span>{{ caseDetail.url || '-' }}</span>
            <strong>请求头</strong><pre>{{ formatJson(caseDetail.request_headers) }}</pre>
            <template v-if="caseDetail.request_body_original !== undefined">
              <strong>请求原文</strong><pre>{{ formatPayloadForDisplay(caseDetail.request_body_original, caseDetail.body_format) }}</pre>
              <template v-if="caseDetail.sm3_signature">
                <strong>SM3签名</strong><pre>{{ formatJson(caseDetail.sm3_signature) }}</pre>
              </template>
              <strong>实际请求报文</strong><pre>{{ formatPayloadForDisplay(caseDetail.request_body, caseDetail.body_format) }}</pre>
            </template>
            <template v-else>
              <strong>请求体</strong><pre>{{ formatPayloadForDisplay(caseDetail.request_body, caseDetail.body_format) }}</pre>
            </template>
            <strong>断言信息</strong><pre>{{ formatJson(caseDetail.assertions) }}</pre>
            <strong>提取规则</strong><pre>{{ formatJson(caseDetail.extractors) }}</pre>
            <template v-if="caseDetail.extracted_variables?.length">
              <strong>本次提取值</strong><pre>{{ formatJson(caseDetail.extracted_variables) }}</pre>
            </template>
            <template v-if="caseDetail.response_snapshot?.decrypted_text !== undefined">
              <strong>响应密文</strong><pre>{{ formatJson(caseDetail.response_snapshot.encrypted_json) }}</pre>
              <strong>响应解密内容</strong><pre>{{ formatPayloadForDisplay(caseDetail.response_snapshot.decrypted_text, caseDetail.body_format) }}</pre>
            </template>
            <template v-else>
              <strong>返回报文</strong><pre>{{ formatResponseSnapshotBody(caseDetail.response_snapshot, caseDetail.body_format) }}</pre>
            </template>
          </div>
          <template #footer>
            <a-button type="primary" @click="caseDetailDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <a-modal v-model:open="executionDetailDialogVisible" title="执行进度" width="820px">
          <a-descriptions v-if="executionDetail.task" :column="3" border>
            <a-descriptions-item label="状态">{{ executionDetail.task.status }}</a-descriptions-item>
            <a-descriptions-item label="汇总">{{ formatJson(executionDetail.task.summary) }}</a-descriptions-item>
          </a-descriptions>
          <a-table :pagination="false" :data-source="executionDetail.results" size="small" class="sub execution-progress-table" :scroll="{ x: 760 }">
            <template #expandedRowRender="{ record: row }">
              <div class="execution-result-expand">
                <strong>参数提取结果</strong>
                <pre>{{ formatJson(row.response_snapshot?.extracted_variables || []) }}</pre>
                <strong>请求快照</strong>
                <pre>{{ formatJson(row.request_snapshot) }}</pre>
                <strong>响应快照</strong>
                <pre>{{ formatJson(row.response_snapshot) }}</pre>
              </div>
            </template>
            <a-table-column title="用例名称"><template #default="{ record: row }"><TableText :value="row.case_name" /></template></a-table-column>
            <a-table-column title="接口"><template #default="{ record: row }"><TableText :value="row.api_name" /></template></a-table-column>
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column data-index="duration_ms" title="耗时(ms)" width="100" />
            <a-table-column title="错误信息"><template #default="{ record: row }"><TableText :value="row.error_message" /></template></a-table-column>
          </a-table>
          <template #footer>
            <a-button type="primary" @click="executionDetailDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <section v-if="active === 'ui-reports'" class="page-view">
          <div class="toolbar">
            <h2>UI测试报告</h2>
            <div class="toolbar-actions">
              <a-button danger :disabled="!selectedUiReportIds.length" @click="deleteSelectedUiReports">批量删除</a-button>
            </div>
          </div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="UI用例名称">
              <a-input v-model:value="uiReportSearch.name" placeholder="请输入UI用例名称" allow-clear @keyup.enter="searchUiReports" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="uiReportSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="queued">排队中</a-select-option>
                <a-select-option value="running">执行中</a-select-option>
                <a-select-option value="passed">已通过</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
                <a-select-option value="error">异常</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchUiReports">搜索</a-button>
              <a-button @click="resetUiReportSearch">重置</a-button>
            </div>
          </a-form>
          <a-table
            :pagination="false"
            :data-source="uiReportList"
            :row-key="(row: any) => row.id"
            :row-selection="{ selectedRowKeys: selectedUiReportIds, onChange: changeSelectedUiReports }"
          >
            <a-table-column title="UI用例名称"><template #default="{ record: row }"><TableText :value="row.target_name" /></template></a-table-column>
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="环境"><template #default="{ record: row }"><TableText :value="row.environment_name" /></template></a-table-column>
            <a-table-column title="执行模式" width="110">
              <template #default="{ record: row }">
                <a-tag :color="row.execution_mode === 'ai' ? 'blue' : 'default'">{{ uiExecutionModeText(row.execution_mode) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行时间" width="150">
              <template #default="{ record: row }">{{ formatMinute(row.ended_at || row.started_at || row.create_date) }}</template>
            </a-table-column>
            <a-table-column data-index="executor_name" title="执行用户" width="120" />
            <a-table-column title="操作" width="230" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openReport(row)">查看报告</a-button>
                  <a-button size="small" @click="exportReport(row)">导出</a-button>
                  <a-button size="small" danger @click="deleteUiReport(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="uiReportPagination.page"
              :page-size="uiReportPagination.pageSize"
              :total="uiReportPagination.total"
              @change="changeUiReportPage"
            />
          </div>
        </section>

        <section v-if="active === 'reports'" class="page-view">
          <div class="toolbar">
            <h2>报告中心</h2>
            <div class="toolbar-actions">
              <a-button danger :disabled="!selectedReportIds.length" @click="deleteSelectedReports">批量删除</a-button>
            </div>
          </div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="测试计划名称">
              <a-input v-model:value="reportSearch.name" placeholder="请输入测试计划名称" allow-clear @keyup.enter="searchReports" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="reportSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="queued">排队中</a-select-option>
                <a-select-option value="running">执行中</a-select-option>
                <a-select-option value="passed">已通过</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
                <a-select-option value="error">异常</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchReports">搜索</a-button>
              <a-button @click="resetReportSearch">重置</a-button>
            </div>
          </a-form>
          <a-table
            :pagination="false"
            :data-source="reportList"
            :row-key="(row: any) => row.id"
            :row-selection="{ selectedRowKeys: selectedReportIds, onChange: changeSelectedReports }"
          >
            <a-table-column title="测试计划名称"><template #default="{ record: row }"><TableText :value="row.target_name" /></template></a-table-column>
            <a-table-column title="项目"><template #default="{ record: row }"><TableText :value="row.project_name" /></template></a-table-column>
            <a-table-column title="环境"><template #default="{ record: row }"><TableText :value="row.environment_name" /></template></a-table-column>
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行时间" width="150">
              <template #default="{ record: row }">{{ formatMinute(row.ended_at || row.started_at || row.create_date) }}</template>
            </a-table-column>
            <a-table-column data-index="executor_name" title="执行用户" width="120" />
            <a-table-column title="操作" width="230" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openReport(row)">查看报告</a-button>
                  <a-button size="small" danger @click="deleteReport(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="reportPagination.page"
              :page-size="reportPagination.pageSize"
              :total="reportPagination.total"
              @change="changeReportPage"
            />
          </div>
        </section>

        <section v-if="active === 'ai_cases'" class="page-view ai-generation-page">
          <div class="toolbar">
            <div><h2>AI生成用例</h2><p class="page-subtitle">上传需求文档，使用 AI 生成测试用例 Excel 文件。</p></div>
          </div>
          <a-card class="ai-generation-upload" :bordered="false">
            <a-form layout="vertical">
              <a-form-item label="需求文档" extra="每次只能上传 1 个文档，文件大小不超过 20MB。">
                <a-upload
                  :file-list="aiSourceFiles"
                  :max-count="1"
                  :multiple="false"
                  :show-upload-list="false"
                  :before-upload="selectAiSourceFile"
                >
                  <a-button :disabled="aiGenerating"><template #icon><FileTextOutlined /></template>选择需求文档</a-button>
                </a-upload>
                <div v-if="aiSourceFiles.length || aiLastUploadedFilename" class="ai-selected-file">
                  <FileTextOutlined />
                  <span :title="aiSourceFiles[0]?.name || aiLastUploadedFilename">{{ aiSourceFiles[0]?.name || aiLastUploadedFilename }}</span>
                  <a-button v-if="aiSourceFiles.length" type="link" size="small" :disabled="aiGenerating" @click="removeAiSourceFile">移除</a-button>
                </div>
              </a-form-item>
              <a-button type="primary" :loading="aiGenerating" :disabled="!aiSourceFiles.length" @click="startAiGeneration">
                <template #icon><PlayCircleOutlined /></template>开始生成
              </a-button>
            </a-form>
          </a-card>

          <div class="toolbar ai-history-toolbar"><h3>生成历史</h3><a-button @click="loadAiGenerations"><template #icon><ReloadOutlined /></template>刷新</a-button></div>
          <a-table :pagination="false" :data-source="aiGenerations" :scroll="{ x: 1080 }" table-layout="fixed" class="ai-generation-table">
            <a-table-column title="编号" :width="64"><template #default="{ index }">{{ aiGenerationSerialNumber(index) }}</template></a-table-column>
            <a-table-column title="需求文档" :width="260">
              <template #default="{ record: row }"><span class="ai-source-filename" :title="row.source_filename">{{ row.source_filename }}</span></template>
            </a-table-column>
            <a-table-column title="状态" :width="96">
              <template #default="{ record: row }"><a-tag :color="aiGenerationStatusColor(row.status)">{{ aiGenerationStatusText(row.status) }}</a-tag></template>
            </a-table-column>
            <a-table-column data-index="creator_name" title="发起人" :width="110" />
            <a-table-column data-index="create_date" title="创建时间" :width="168" />
            <a-table-column title="生成文件" :width="190">
              <template #default="{ record: row }">
                <div v-if="row.output_files?.length" class="ai-output-files">
                  <a-button v-for="(file, index) in row.output_files" :key="file.storage_name || index" size="small" type="link" @click="downloadAiGenerationFile(row, index)">{{ file.name }}</a-button>
                </div>
                <span v-else>-</span>
              </template>
            </a-table-column>
            <a-table-column title="错误信息" :width="190">
              <template #default="{ record: row }"><span class="ai-error-message" :title="row.error_message || ''">{{ row.error_message || '-' }}</span></template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination :show-total="paginationTotal" show-less-items :current="aiGenerationPagination.page" :page-size="aiGenerationPagination.pageSize" :total="aiGenerationPagination.total" @change="changeAiGenerationPage" />
          </div>
        </section>

        <section v-if="active === 'knowledge_projects'" class="page-view">
          <div class="toolbar"><h2>项目配置</h2><a-button type="primary" @click="openCreateKnowledgeProject"><template #icon><PlusOutlined /></template>创建项目</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目名称"><a-input v-model:value="knowledgeProjectSearch.name" placeholder="请输入项目名称" allow-clear @keyup.enter="searchKnowledgeProjects" /></a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="knowledgeProjectSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchKnowledgeProjects">搜索</a-button><a-button @click="resetKnowledgeProjectSearch">重置</a-button></div>
          </a-form>
          <a-table :pagination="false" :data-source="knowledgeProjectList">
            <a-table-column title="编号" width="70"><template #default="{ index }">{{ knowledgeProjectSerialNumber(index) }}</template></a-table-column>
            <a-table-column title="项目名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="描述"><template #default="{ record: row }"><TableText :value="row.description" /></template></a-table-column>
            <a-table-column title="状态" width="100"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'warning'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditKnowledgeProject(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteKnowledgeProject(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="knowledgeProjectPagination.page" :page-size="knowledgeProjectPagination.pageSize" :total="knowledgeProjectPagination.total" @change="changeKnowledgeProjectPage" /></div>

          <a-modal v-model:open="knowledgeProjectFormVisible" :title="knowledgeProjectForm.id ? '编辑知识库项目' : '创建知识库项目'" width="460px" @after-close="resetKnowledgeProjectForm">
            <a-form layout="vertical">
              <a-form-item label="项目名称" required><a-input v-model:value="knowledgeProjectForm.name" placeholder="请输入项目名称" /></a-form-item>
              <a-form-item label="描述"><a-textarea v-model:value="knowledgeProjectForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="请输入描述" /></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="knowledgeProjectForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
            </a-form>
            <template #footer><a-button @click="knowledgeProjectFormVisible = false">取消</a-button><a-button type="primary" @click="saveKnowledgeProject">确认</a-button></template>
          </a-modal>
        </section>

        <section v-if="active === 'knowledge_bases'" class="page-view knowledge-page">
          <div class="toolbar">
            <div><h2>知识库配置</h2><p class="page-subtitle">按知识库项目绑定 Dify 已配置知识库，查看文档并检索命中片段。</p></div>
            <a-button type="primary" @click="openCreateKnowledgeBase"><template #icon><PlusOutlined /></template>新增绑定</a-button>
          </div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="knowledgeSearch.project_id" placeholder="请选择项目" allow-clear>
                <a-select-option v-for="p in knowledgeProjects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="知识库名称"><a-input v-model:value="knowledgeSearch.name" placeholder="请输入知识库名称" allow-clear @keyup.enter="searchKnowledgeBases" /></a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="knowledgeSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchKnowledgeBases">搜索</a-button><a-button @click="resetKnowledgeSearch">重置</a-button></div>
          </a-form>
          <a-table class="knowledge-base-table" table-layout="fixed" :pagination="false" :data-source="knowledgeBases" :scroll="{ x: 1168 }">
            <a-table-column title="编号" width="56" class-name="knowledge-number-column"><template #default="{ index }">{{ knowledgeSerialNumber(index) }}</template></a-table-column>
            <a-table-column data-index="project_name" title="项目" width="170" />
            <a-table-column title="知识库名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="Dify Dataset ID" width="180">
              <template #default="{ record: row }">
                <a-tooltip :title="row.dify_dataset_id">
                  <TableText :value="maskDatasetId(row.dify_dataset_id)" :max-width="180" />
                </a-tooltip>
              </template>
            </a-table-column>
            <a-table-column title="状态" width="72" class-name="knowledge-status-column"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'warning'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="330" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openKnowledgeDocuments(row)">文档</a-button>
                  <a-button size="small" type="primary" :disabled="row.status !== 'active'" @click="openKnowledgeRetrieve(row)">检索</a-button>
                  <a-button size="small" @click="checkKnowledgeBase(row)">测试</a-button>
                  <a-button size="small" @click="openEditKnowledgeBase(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteKnowledgeBase(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="knowledgePagination.page" :page-size="knowledgePagination.pageSize" :total="knowledgePagination.total" @change="changeKnowledgePage" /></div>

          <a-modal v-model:open="knowledgeFormVisible" :title="knowledgeForm.id ? '编辑知识库绑定' : '新增知识库绑定'" width="560px" @after-close="resetKnowledgeForm">
            <a-form layout="vertical">
              <a-form-item label="项目" required><a-select v-model:value="knowledgeForm.project_id" placeholder="请选择项目"><a-select-option v-for="p in activeKnowledgeProjects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="知识库名称" required><a-input v-model:value="knowledgeForm.name" placeholder="例如：支付业务规则" /></a-form-item>
              <a-form-item label="Dify 知识库" required>
                <a-select
                  v-model:value="knowledgeForm.dify_dataset_id"
                  show-search
                  allow-clear
                  :loading="difyDatasetsLoading"
                  placeholder="请选择 Dify 知识库"
                  :filter-option="filterDifyDatasetOption"
                  @dropdown-visible-change="handleDifyDatasetDropdown"
                  @change="changeDifyDataset"
                >
                  <a-select-option v-for="item in difyDatasets" :key="item.id" :value="item.id" :title="item.name">
                    {{ item.name }}
                  </a-select-option>
                </a-select>
                <div v-if="knowledgeForm.dify_dataset_id" class="form-tip">Dataset ID：{{ knowledgeForm.dify_dataset_id }}</div>
              </a-form-item>
              <a-form-item label="状态"><a-select v-model:value="knowledgeForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="备注"><a-textarea v-model:value="knowledgeForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="可记录知识库用途或维护人" /></a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="knowledgeFormVisible = false">取消</a-button>
              <a-button :loading="knowledgeChecking" @click="checkKnowledgeForm">连接测试</a-button>
              <a-button type="primary" @click="saveKnowledgeBase">确认</a-button>
            </template>
          </a-modal>

          <a-drawer v-model:open="knowledgeDocumentsVisible" width="760" :title="`${selectedKnowledgeBase?.name || '知识库'}文档`">
            <a-form class="search-form compact-search-form" layout="vertical">
              <a-form-item label="关键词"><a-input v-model:value="knowledgeDocumentSearch.keyword" placeholder="请输入文档关键词" allow-clear @keyup.enter="searchKnowledgeDocuments" /></a-form-item>
                            <a-form-item label="索引状态">
                <a-select v-model:value="knowledgeDocumentSearch.status" placeholder="请选择索引状态" allow-clear>
                  <a-select-option value="completed">索引完成</a-select-option>
                  <a-select-option value="indexing">索引中</a-select-option>
                  <a-select-option value="processing">处理中</a-select-option>
                  <a-select-option value="error">索引异常</a-select-option>
                  <a-select-option value="failed">索引失败</a-select-option>
                  <a-select-option value="paused">已暂停</a-select-option>
                </a-select>
              </a-form-item>
              <div class="search-actions"><a-button type="primary" @click="searchKnowledgeDocuments">搜索</a-button><a-button @click="resetKnowledgeDocuments">重置</a-button></div>
            </a-form>
            <a-table :pagination="false" :data-source="knowledgeDocuments" :loading="knowledgeDocumentsLoading" :scroll="{ x: 720 }">
              <a-table-column title="文档名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
              <a-table-column data-index="indexing_status" title="索引状态" width="120" />
              <a-table-column title="启用" width="80"><template #default="{ record: row }"><a-tag :color="row.enabled ? 'success' : 'warning'">{{ row.enabled ? '是' : '否' }}</a-tag></template></a-table-column>
              <a-table-column data-index="word_count" title="字数" width="90" />
              <a-table-column data-index="hit_count" title="命中" width="90" />
              <a-table-column data-index="update_date" title="更新时间" width="160" />
            </a-table>
            <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="knowledgeDocumentPagination.page" :page-size="knowledgeDocumentPagination.pageSize" :total="knowledgeDocumentPagination.total" @change="changeKnowledgeDocumentPage" /></div>
          </a-drawer>

          <a-modal v-model:open="knowledgeRetrieveVisible" :title="`${selectedKnowledgeBase?.name || '知识库'}检索`" width="780px">
            <a-form layout="vertical">
              <a-form-item label="检索内容" required><a-textarea v-model:value="knowledgeRetrieveForm.query" :auto-size="{ minRows: 3, maxRows: 6 }" placeholder="请输入要检索的问题或关键词" /></a-form-item>
              <div class="knowledge-retrieve-options">
                <a-form-item label="Top K"><a-input-number v-model:value="knowledgeRetrieveForm.top_k" :min="1" :max="10" /></a-form-item>
                <a-form-item label="分数阈值"><a-input-number v-model:value="knowledgeRetrieveForm.score_threshold" :min="0" :max="1" :step="0.05" placeholder="可选" /></a-form-item>
              </div>
            </a-form>
            <div v-if="knowledgeRetrieveResult.length" class="knowledge-hit-list">
              <div v-for="(hit, index) in knowledgeRetrieveResult" :key="hit.segment_id || index" class="knowledge-hit-item">
                <div class="knowledge-hit-head"><strong>命中 {{ index + 1 }}</strong><a-tag color="blue">score {{ formatScore(hit.score) }}</a-tag><span>{{ hit.document_name || hit.document_id || '-' }}</span></div>
                <p>{{ hit.content }}</p>
              </div>
            </div>
            <a-empty v-else-if="knowledgeRetrieved" description="暂无命中结果" />
            <template #footer><a-button @click="knowledgeRetrieveVisible = false">关闭</a-button><a-button type="primary" :loading="knowledgeRetrieving" @click="runKnowledgeRetrieve">开始检索</a-button></template>
          </a-modal>
        </section>

        <section v-if="active === 'knowledge_workflows'" class="page-view knowledge-page">
          <div class="toolbar">
            <div><h2>工作流配置</h2><p class="page-subtitle">绑定 Dify Workflow，供知识问答页面调用。</p></div>
            <a-button type="primary" @click="openCreateKnowledgeWorkflow"><template #icon><PlusOutlined /></template>新增工作流</a-button>
          </div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="工作流名称"><a-input v-model:value="knowledgeWorkflowSearch.name" placeholder="请输入工作流名称" allow-clear @keyup.enter="searchKnowledgeWorkflows" /></a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="knowledgeWorkflowSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions"><a-button type="primary" @click="searchKnowledgeWorkflows">搜索</a-button><a-button @click="resetKnowledgeWorkflowSearch">重置</a-button></div>
          </a-form>
          <a-table :pagination="false" :data-source="knowledgeWorkflowList" :scroll="{ x: 960 }">
            <a-table-column title="编号" width="70"><template #default="{ index }">{{ knowledgeWorkflowSerialNumber(index) }}</template></a-table-column>
            <a-table-column title="工作流名称"><template #default="{ record: row }"><TableText :value="row.name" /></template></a-table-column>
            <a-table-column title="API 地址"><template #default="{ record: row }"><TableText :value="row.api_base_url" /></template></a-table-column>
            <a-table-column title="API Key 环境变量"><template #default="{ record: row }"><TableText :value="row.api_key_env" /></template></a-table-column>
            <a-table-column title="状态" width="90"><template #default="{ record: row }"><a-tag :color="row.status === 'active' ? 'success' : 'warning'">{{ row.status === 'active' ? '启用' : '禁用' }}</a-tag></template></a-table-column>
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="260" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" :loading="knowledgeWorkflowCheckingId === row.id" @click="checkKnowledgeWorkflow(row)">测试</a-button>
                  <a-button size="small" @click="openEditKnowledgeWorkflow(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteKnowledgeWorkflow(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination"><a-pagination :show-total="paginationTotal" show-less-items :current="knowledgeWorkflowPagination.page" :page-size="knowledgeWorkflowPagination.pageSize" :total="knowledgeWorkflowPagination.total" @change="changeKnowledgeWorkflowPage" /></div>

          <a-modal v-model:open="knowledgeWorkflowFormVisible" :title="knowledgeWorkflowForm.id ? '编辑工作流配置' : '新增工作流配置'" width="560px" @after-close="resetKnowledgeWorkflowForm">
            <a-form layout="vertical">
              <a-form-item label="工作流名称" required><a-input v-model:value="knowledgeWorkflowForm.name" placeholder="例如：FAF知识库问答工作流" /></a-form-item>
              <a-form-item label="Dify API 地址"><a-input v-model:value="knowledgeWorkflowForm.api_base_url" placeholder="留空使用全局 DIFY_API_BASE_URL" /></a-form-item>
              <a-form-item label="API Key 环境变量名" required><a-select v-model:value="knowledgeWorkflowForm.api_key_env" placeholder="请选择 API Key 配置" show-search option-filter-prop="label" @dropdown-visible-change="handleWorkflowApiKeyDropdown"><a-select-option v-for="item in workflowApiKeyOptions" :key="item.env_key" :value="item.env_key" :label="`${item.display_name} ${item.env_key}`">{{ item.display_name }}（{{ item.env_key }}）<span class="option-status">{{ item.configured ? '' : '未配置' }}</span></a-select-option></a-select></a-form-item>
              <a-form-item label="状态"><a-select v-model:value="knowledgeWorkflowForm.status"><a-select-option value="active">启用</a-select-option><a-select-option value="disabled">禁用</a-select-option></a-select></a-form-item>
              <a-form-item label="备注"><a-textarea v-model:value="knowledgeWorkflowForm.description" :auto-size="{ minRows: 2, maxRows: 4 }" placeholder="可记录工作流用途或 Dify 配置说明" /></a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="knowledgeWorkflowFormVisible = false">取消</a-button>
              <a-button type="primary" @click="saveKnowledgeWorkflow">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'knowledge_qa'" class="page-view knowledge-qa-page">
          <div class="toolbar">
            <div><h2>知识问答</h2><p class="page-subtitle">基于 Dify Workflow 进行知识库问答，同一会话内支持连续追问。</p></div>
            <a-button type="primary" @click="openCreateQaSession"><template #icon><PlusOutlined /></template>新建会话</a-button>
          </div>
          <div class="qa-shell">
            <aside class="qa-sessions">
              <div class="qa-session-filter">
                <a-select v-model:value="qaSessionSearch.project_id" placeholder="项目" allow-clear @change="searchQaSessions">
                  <a-select-option v-for="p in knowledgeProjects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </div>
              <div class="qa-session-list">
                <button v-for="session in qaSessions" :key="session.id" class="qa-session-item" :class="{ active: selectedQaSession?.id === session.id }" @click="selectQaSession(session)">
                  <strong>{{ session.title }}</strong>
                  <span>{{ session.project_name }} / {{ session.workflow_name }}</span>
                </button>
                <a-empty v-if="!qaSessions.length" description="暂无会话" />
              </div>
            </aside>
            <main class="qa-chat">
              <div v-if="selectedQaSession" class="qa-chat-head">
                <div><strong>{{ selectedQaSession.title }}</strong><span>{{ selectedQaSession.project_name }} / {{ selectedQaSession.workflow_name }}</span></div>
                <a-button size="small" danger @click="deleteQaSession(selectedQaSession)">删除会话</a-button>
              </div>
              <div ref="qaMessagesRef" class="qa-messages">
                <template v-if="selectedQaSession">
                  <div v-for="msg in qaMessages" :key="msg.id" class="qa-message" :class="`qa-message-${msg.role}`">
                    <div class="qa-message-role">{{ msg.role === 'user' ? '我' : '助手' }}</div>
                    <div class="qa-message-content">{{ msg.error_message || msg.content }}</div>
                  </div>
                  <a-empty v-if="!qaMessages.length" description="当前会话暂无消息" />
                </template>
                <a-empty v-else description="请选择或新建会话" />
              </div>
              <div class="qa-input-bar">
                <a-textarea v-model:value="qaQuestion" :disabled="!selectedQaSession" :auto-size="{ minRows: 2, maxRows: 5 }" placeholder="请输入问题" @keydown.ctrl.enter.prevent="askKnowledgeQa" />
                <a-button type="primary" :disabled="!selectedQaSession" :loading="qaAsking" @click="askKnowledgeQa">发送</a-button>
              </div>
            </main>
          </div>

          <a-modal v-model:open="qaSessionFormVisible" title="新建知识问答会话" width="520px" @after-close="resetQaSessionForm">
            <a-form layout="vertical">
              <a-form-item label="项目" required><a-select v-model:value="qaSessionForm.project_id" placeholder="请选择项目" @change="changeQaSessionProject"><a-select-option v-for="p in activeKnowledgeProjects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="工作流" required><a-select v-model:value="qaSessionForm.workflow_id" placeholder="请选择工作流"><a-select-option v-for="w in qaSessionWorkflows" :key="w.id" :value="w.id">{{ w.name }}</a-select-option></a-select></a-form-item>
              <a-form-item label="会话标题"><a-input v-model:value="qaSessionForm.title" placeholder="留空则用第一条问题自动命名" /></a-form-item>
            </a-form>
            <template #footer><a-button @click="qaSessionFormVisible = false">取消</a-button><a-button type="primary" @click="createQaSession">确认</a-button></template>
          </a-modal>
        </section>
        <section v-if="active === 'logs'" class="page-view">
          <div class="toolbar"><h2>日志中心</h2></div>
          <a-tabs v-model:active-key="activeLogTab" class="log-tabs" @change="changeLogTab">
            <a-tab-pane key="operations" tab="操作日志">
              <a-form class="search-form log-search-form" layout="vertical">
                <a-form-item label="模块"><a-input v-model:value="operationLogSearch.module" placeholder="如：项目、接口、用例" allow-clear @keyup.enter="searchOperationLogs" /></a-form-item>
                <a-form-item label="操作"><a-input v-model:value="operationLogSearch.action" placeholder="如：创建、编辑、删除" allow-clear @keyup.enter="searchOperationLogs" /></a-form-item>
                <a-form-item label="结果">
                  <a-select v-model:value="operationLogSearch.result" placeholder="请选择结果" allow-clear>
                    <a-select-option value="success">成功</a-select-option>
                    <a-select-option value="failed">失败</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="开始时间"><a-input v-model:value="operationLogSearch.start_time" placeholder="yyyy-MM-dd HH:mm:ss" allow-clear /></a-form-item>
                <a-form-item label="结束时间"><a-input v-model:value="operationLogSearch.end_time" placeholder="yyyy-MM-dd HH:mm:ss" allow-clear /></a-form-item>
                <div class="search-actions">
                  <a-button type="primary" @click="searchOperationLogs">搜索</a-button>
                  <a-button @click="resetOperationLogSearch">重置</a-button>
                </div>
              </a-form>
              <a-table :pagination="false" :data-source="operationLogs" :scroll="{ x: 1040 }" class="log-table">
                <a-table-column title="模块" width="120">
                  <template #default="{ record: row }">{{ operationModuleText(row.module) }}</template>
                </a-table-column>
                <a-table-column title="操作" width="130">
                  <template #default="{ record: row }">{{ operationActionText(row.action) }}</template>
                </a-table-column>
                <a-table-column data-index="operator_name" title="用户" width="130" />
                <a-table-column title="结果" width="100">
                  <template #default="{ record: row }"><a-tag :color="row.result === 'success' ? 'success' : 'error'">{{ operationResultText(row.result) }}</a-tag></template>
                </a-table-column>
                <a-table-column title="内容" class-name="log-wrap-cell">
                  <template #default="{ record: row }">{{ operationContentText(row.content) }}</template>
                </a-table-column>
                <a-table-column data-index="create_date" title="时间" width="160" />
                <a-table-column title="操作" width="90">
                  <template #default="{ record: row }"><a-button size="small" @click="openOperationLogDetail(row)">详情</a-button></template>
                </a-table-column>
              </a-table>
              <div class="pagination">
                <a-pagination :show-total="paginationTotal" show-less-items :current="operationLogPagination.page" :page-size="operationLogPagination.pageSize" :total="operationLogPagination.total" @change="changeOperationLogPage" />
              </div>
            </a-tab-pane>
            <a-tab-pane key="executions" tab="执行日志">
              <a-form class="search-form log-search-form" layout="vertical">
                <a-form-item label="名称"><a-input v-model:value="executionLogSearch.name" placeholder="计划 / 用例 / 接口" allow-clear @keyup.enter="searchExecutionLogs" /></a-form-item>
                <a-form-item label="状态">
                  <a-select v-model:value="executionLogSearch.status" placeholder="请选择状态" allow-clear>
                    <a-select-option value="passed">通过</a-select-option>
                    <a-select-option value="failed">失败</a-select-option>
                    <a-select-option value="error">异常</a-select-option>
                  </a-select>
                </a-form-item>
                <div class="search-actions">
                  <a-button type="primary" @click="searchExecutionLogs">搜索</a-button>
                  <a-button @click="resetExecutionLogSearch">重置</a-button>
                </div>
              </a-form>
              <a-table :pagination="false" :data-source="executionLogs" :scroll="{ x: 1160 }" class="log-table">
                <a-table-column title="计划/目标"><template #default="{ record: row }"><TableText :value="row.target_name" /></template></a-table-column>
                <a-table-column title="用例"><template #default="{ record: row }"><TableText :value="row.case_name" /></template></a-table-column>
                <a-table-column title="接口"><template #default="{ record: row }"><TableText :value="row.api_name" /></template></a-table-column>
                <a-table-column data-index="environment_name" title="环境" width="130" />
                <a-table-column title="状态" width="100">
                  <template #default="{ record: row }"><a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag></template>
                </a-table-column>
                <a-table-column data-index="duration_ms" title="耗时(ms)" width="100" />
                <a-table-column data-index="create_date" title="时间" width="160" />
                <a-table-column title="操作" width="160">
                  <template #default="{ record: row }">
                    <div class="table-actions">
                      <a-button size="small" @click="openExecutionLogDetail(row)">详情</a-button>
                      <a-button size="small" @click="openExecutionLogReport(row)">报告</a-button>
                    </div>
                  </template>
                </a-table-column>
              </a-table>
              <div class="pagination">
                <a-pagination :show-total="paginationTotal" show-less-items :current="executionLogPagination.page" :page-size="executionLogPagination.pageSize" :total="executionLogPagination.total" @change="changeExecutionLogPage" />
              </div>
            </a-tab-pane>
            <a-tab-pane key="exceptions" tab="异常日志">
              <a-form class="search-form log-search-form" layout="vertical">
                <a-form-item label="关键字"><a-input v-model:value="exceptionLogSearch.name" placeholder="请求路径 / 异常类型 / 异常摘要" allow-clear @keyup.enter="searchExceptionLogs" /></a-form-item>
                <a-form-item label="结果">
                  <a-select v-model:value="exceptionLogSearch.status" placeholder="请选择结果" allow-clear>
                    <a-select-option value="error">异常</a-select-option>
                  </a-select>
                </a-form-item>
                <div class="search-actions">
                  <a-button type="primary" @click="searchExceptionLogs">搜索</a-button>
                  <a-button @click="resetExceptionLogSearch">重置</a-button>
                </div>
              </a-form>
              <a-table :pagination="false" :data-source="exceptionLogs" :scroll="{ x: 1060 }" class="log-table">
                <a-table-column title="请求路径"><template #default="{ record: row }"><TableText :value="row.path" /></template></a-table-column>
                <a-table-column data-index="method" title="方法" width="90" />
                <a-table-column title="异常类型"><template #default="{ record: row }"><TableText :value="row.error_type" /></template></a-table-column>
                <a-table-column title="结果" width="90">
                  <template #default="{ record: row }"><a-tag color="error">{{ operationResultText(row.result) }}</a-tag></template>
                </a-table-column>
                <a-table-column title="异常摘要"><template #default="{ record: row }"><TableText :value="row.error_message" /></template></a-table-column>
                <a-table-column data-index="ip" title="IP" width="130" />
                <a-table-column data-index="create_date" title="时间" width="160" />
                <a-table-column title="操作" width="90">
                  <template #default="{ record: row }"><a-button size="small" @click="openOperationLogDetail(row)">详情</a-button></template>
                </a-table-column>
              </a-table>
              <div class="pagination">
                <a-pagination :show-total="paginationTotal" show-less-items :current="exceptionLogPagination.page" :page-size="exceptionLogPagination.pageSize" :total="exceptionLogPagination.total" @change="changeExceptionLogPage" />
              </div>
            </a-tab-pane>
          </a-tabs>
        </section>

        <a-modal v-model:open="operationLogDetailVisible" title="操作日志详情" width="720px">
          <a-descriptions v-if="operationLogDetail" :column="2" border>
            <a-descriptions-item label="模块">{{ operationModuleText(operationLogDetail.module) }}</a-descriptions-item>
            <a-descriptions-item label="操作">{{ operationActionText(operationLogDetail.action) }}</a-descriptions-item>
            <a-descriptions-item label="结果">{{ operationResultText(operationLogDetail.result) }}</a-descriptions-item>
            <a-descriptions-item label="用户">{{ operationLogDetail.operator_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="IP">{{ operationLogDetail.ip || '-' }}</a-descriptions-item>
            <a-descriptions-item label="时间">{{ operationLogDetail.create_date }}</a-descriptions-item>
          </a-descriptions>
          <div class="log-detail-block"><strong>内容</strong><pre>{{ operationContentText(operationLogDetail?.content) }}</pre></div>
          <template #footer><a-button type="primary" @click="operationLogDetailVisible = false">关闭</a-button></template>
        </a-modal>

        <a-modal v-model:open="executionLogDetailVisible" title="执行日志详情" width="920px">
          <a-descriptions v-if="executionLogDetail" :column="3" border>
            <a-descriptions-item label="计划/目标">{{ executionLogDetail.target_name }}</a-descriptions-item>
            <a-descriptions-item label="状态"><a-tag :color="executionStatusColor(executionLogDetail.status)">{{ executionStatusText(executionLogDetail.status) }}</a-tag></a-descriptions-item>
            <a-descriptions-item label="用例">{{ executionLogDetail.case_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="接口">{{ executionLogDetail.api_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="耗时">{{ executionLogDetail.duration_ms }} ms</a-descriptions-item>
          </a-descriptions>
          <div class="execution-result-expand log-detail-block">
            <strong>请求头</strong><pre>{{ formatJson(executionLogDetail?.request_snapshot?.headers || {}) }}</pre>
            <strong>请求参数</strong><pre>{{ formatJson(executionLogDetail?.request_snapshot?.query || {}) }}</pre>
            <template v-if="executionLogDetail?.request_snapshot?.body_original !== undefined">
              <strong>请求原文</strong><pre>{{ formatPayloadForDisplay(executionLogDetail?.request_snapshot?.body_original || '') }}</pre>
            </template>
            <template v-if="executionLogDetail?.request_snapshot?.sm3_signature">
              <strong>SM3签名</strong><pre>{{ formatJson(executionLogDetail?.request_snapshot?.sm3_signature) }}</pre>
            </template>
            <strong>请求报文</strong><pre>{{ formatPayloadForDisplay(executionLogDetail?.request_snapshot?.body || '') }}</pre>
            <strong>响应状态</strong><pre>{{ formatJson({ status_code: executionLogDetail?.response_snapshot?.status_code, duration_ms: executionLogDetail?.response_snapshot?.duration_ms }) }}</pre>
            <strong>响应报文</strong><pre>{{ formatResponseSnapshotBody(executionLogDetail?.response_snapshot || {}) }}</pre>
            <strong>断言结果</strong><pre>{{ formatJson(executionLogDetail?.assertion_results || []) }}</pre>
            <strong>提取变量</strong><pre>{{ formatJson(executionLogDetail?.response_snapshot?.extracted_variables || []) }}</pre>
          </div>
          <template #footer><a-button type="primary" @click="executionLogDetailVisible = false">关闭</a-button></template>
        </a-modal>

        <a-modal v-model:open="changePasswordDialogVisible" title="修改密码" width="420px" @after-close="resetChangePasswordForm">
          <a-form layout="vertical" @submit.prevent="changePassword">
            <a-form-item label="原密码">
              <a-input-password v-model:value="changePasswordForm.old_password" placeholder="请输入原密码" />
            </a-form-item>
            <a-form-item label="新密码">
              <a-input-password
                v-model:value="changePasswordForm.new_password"
                placeholder="请输入新密码"
                @blur="validatePasswordMatch"
              />
            </a-form-item>
            <a-form-item label="确认密码">
              <a-input-password
                v-model:value="changePasswordForm.confirm_password"
                placeholder="请再次输入新密码"
                @blur="validatePasswordMatch"
              />
            </a-form-item>
          </a-form>
          <template #footer>
            <a-button @click="cancelChangePassword">取消</a-button>
            <a-button type="primary" @click="changePassword">确认</a-button>
          </template>
        </a-modal>
      </a-layout-content>
    </a-layout>
  </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { basicSetup } from 'codemirror'
import { json as jsonLanguage } from '@codemirror/lang-json'
import { xml as xmlLanguage } from '@codemirror/lang-xml'
import { indentWithTab } from '@codemirror/commands'
import { Compartment } from '@codemirror/state'
import { EditorView, keymap, placeholder as editorPlaceholder, scrollPastEnd } from '@codemirror/view'
import {
  ApiOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  DeleteOutlined,
  DesktopOutlined,
  DownOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  FileTextOutlined,
  LockOutlined,
  LoginOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  ProfileOutlined,
  ProjectOutlined,
  ReloadOutlined,
  SaveOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
  UserAddOutlined,
  UserOutlined
} from '@ant-design/icons-vue'
import { api, type User } from './api'
import TableText from './components/TableText.vue'

const appTheme = {
  token: {
    colorPrimary: '#1677ff',
    colorInfo: '#1677ff',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorBgLayout: '#f5f7fa',
    colorText: '#1f2937',
    colorTextSecondary: '#667085',
    colorBorder: '#e6eaf0',
    borderRadius: 6,
    controlHeight: 34,
    fontSize: 14
  },
  components: {
    Button: { borderRadius: 6, controlHeightSM: 30 },
    Card: { borderRadiusLG: 8 },
    Input: { activeShadow: '0 0 0 2px rgba(22, 119, 255, 0.12)' },
    Select: { optionSelectedBg: '#eef6ff' },
    Table: { headerBg: '#f8fafc', rowHoverBg: '#f5f9ff' }
  }
}

type AppTab = { name: string; label: string; closable: boolean }
type MenuNode = { key: string; label: string; icon: any; children?: MenuNode[] }
type KeyValueRow = { id: number; key: string; value: string }
type AssertionTarget = 'status' | 'duration' | 'jsonpath' | 'xmlpath' | 'text'
type AssertionCheck = 'equal' | 'exists' | 'not_empty' | 'lt' | 'contains'
type CaseAssertionRow = {
  id: number
  type: string
  target: AssertionTarget
  check: AssertionCheck
  path: string
  expected: string | number | null
}
type CaseExtractorRow = { id: number; name: string; path: string; source: 'jsonpath' | 'xmlpath' | 'regex' }
type MockBodyFormat = 'json' | 'xml' | 'text'
type MockFormState = {
  id?: number
  project_id?: number
  environment_id?: number
  name: string
  method: string
  path: string
  status: string
  status_code: string
  delay_ms: string
  headerRows: KeyValueRow[]
  response_body: string
  body_format: MockBodyFormat
  sm3_enabled: boolean
  description: string
}
type UiStepRow = {
  id: number
  action: string
  locator_type: string
  target: string
  value: string
  description: string
}
type UiRecordAction = 'click' | 'fill' | 'select' | 'assert_visible' | 'assert_text'
type UiCaseFormState = {
  id?: number
  project_id?: number
  environment_id?: number
  name: string
  start_url: string
  description: string
  execution_mode: 'ai' | 'advanced'
  test_goal: string
  test_data_text: string
  assertion_goal: string
  max_steps: number
  step_timeout_ms: number
  allow_ai_actions: boolean
  status: string
  browser_channel: 'chromium' | 'chrome' | 'msedge'
  headless: boolean
  wait_until: 'domcontentloaded' | 'load' | 'networkidle'
  wait_after_load_ms: number
  steps: UiStepRow[]
}

function confirmAction(
  content: string,
  title: string,
  options: { confirmButtonText?: string; cancelButtonText?: string; type?: string; distinguishCancelAndClose?: boolean } = {}
) {
  return new Promise<void>((resolve, reject) => {
    Modal.confirm({
      title,
      content,
      okText: options.confirmButtonText || '确认',
      cancelText: options.cancelButtonText || '取消',
      onOk: () => resolve(),
      onCancel: () => reject('cancel')
    })
  })
}
type ApiEncryption = {
  enabled: boolean
  mode: 'none' | 'rsa_aes_sm3'
  encryptRequest: boolean
  decryptResponse: boolean
  sm3Signature: boolean
}
type ApiAuth = {
  type: 'none' | 'bearer' | 'basic' | 'api_key' | 'oauth2_client_credentials'
  addTo: 'headers' | 'query'
  headerName: string
  headerPrefix: string
  token: string
  username: string
  password: string
  apiKeyName: string
  apiKeyValue: string
  tokenUrl: string
  grantType: string
  clientId: string
  clientSecret: string
  scope: string
  audience: string
  clientAuthentication: 'body' | 'basic'
  verifyTls: boolean
  currentToken: string
  loading: boolean
}
type ApiEditor = {
  tabName: string
  label: string
  mode: 'create' | 'edit'
  apiId?: number
  project_id?: number
  name: string
  description: string
  method: string
  path: string
  bodyFormat: 'json' | 'xml' | 'x-www-form-data'
  bodyTemplate: string
  activePanel: '' | 'query' | 'headers' | 'auth' | 'body' | 'pre-script' | 'encryption' | 'sm3-signature'
  queryRows: KeyValueRow[]
  headerRows: KeyValueRow[]
  preScript: string
  encryption: ApiEncryption
  auth: ApiAuth
  dirty: boolean
}

type BodyEditorLanguage = ApiEditor['bodyFormat'] | 'text'

function bodyEditorLanguageExtension(language: BodyEditorLanguage) {
  if (language === 'text') return []
  return language === 'xml' ? xmlLanguage() : jsonLanguage()
}

const BodyCodeEditor = defineComponent({
  name: 'BodyCodeEditor',
  props: {
    modelValue: { type: String, default: '' },
    language: { type: String as () => BodyEditorLanguage, default: 'json' },
    placeholder: { type: String, default: '' },
    minHeight: { type: String, default: '220px' }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const host = ref<HTMLElement | null>(null)
    const languageCompartment = new Compartment()
    const placeholderCompartment = new Compartment()
    let view: EditorView | null = null

    onMounted(() => {
      if (!host.value) return
      view = new EditorView({
        doc: props.modelValue,
        parent: host.value,
        extensions: [
          basicSetup,
          keymap.of([indentWithTab]),
          EditorView.lineWrapping,
          scrollPastEnd(),
          languageCompartment.of(bodyEditorLanguageExtension(props.language)),
          placeholderCompartment.of(editorPlaceholder(props.placeholder)),
          EditorView.updateListener.of(update => {
            if (update.docChanged) {
              emit('update:modelValue', update.state.doc.toString())
            }
          }),
          EditorView.theme({
            '&': {
              minHeight: props.minHeight,
              maxHeight: '70vh',
              border: '1px solid #d9dff0',
              borderRadius: '6px',
              backgroundColor: '#fff',
              fontSize: '13px'
            },
            '&.cm-focused': {
              outline: 'none',
              borderColor: '#1677ff',
              boxShadow: '0 0 0 2px rgba(22, 119, 255, 0.12)'
            },
            '.cm-scroller': {
              minHeight: props.minHeight,
              maxHeight: '70vh',
              overflow: 'auto',
              fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", monospace'
            },
            '.cm-content': {
              padding: '10px 0 56px'
            },
            '.cm-line': {
              padding: '0 12px'
            },
            '.cm-selectionBackground, &.cm-focused .cm-selectionBackground': {
              backgroundColor: 'rgba(22, 119, 255, 0.28)'
            },
            '.cm-content ::selection': {
              backgroundColor: 'rgba(22, 119, 255, 0.28)'
            },
            '.cm-placeholder': {
              color: '#a8b0bd'
            }
          })
        ]
      })
    })

    watch(() => props.modelValue, value => {
      if (!view) return
      const current = view.state.doc.toString()
      if (value !== current) {
        view.dispatch({ changes: { from: 0, to: current.length, insert: value || '' } })
      }
    })

    watch(() => props.language, language => {
      if (!view) return
      view.dispatch({ effects: languageCompartment.reconfigure(bodyEditorLanguageExtension(language)) })
    })

    watch(() => props.placeholder, value => {
      if (!view) return
      view.dispatch({ effects: placeholderCompartment.reconfigure(editorPlaceholder(value || '')) })
    })

    onBeforeUnmount(() => {
      view?.destroy()
      view = null
    })

    return () => h('div', { ref: host, class: 'body-code-editor' })
  }
})

type PlanEditor = {
  tabName: string
  label: string
  mode: 'create' | 'edit'
  planId?: number
  project_id?: number
  environment_id?: number
  api_id?: number
  name: string
  candidateCases: any[]
  selectedCases: any[]
  queue: any[]
  dragIndex?: number
  dirty: boolean
}

const menuMeta: Record<string, AppTab> = {
  dashboard: { name: 'dashboard', label: '数据概览', closable: false },
  projects: { name: 'projects', label: '项目管理', closable: true },
  environments: { name: 'environments', label: '环境管理', closable: true },
  apis: { name: 'apis', label: '接口管理', closable: true },
  mocks: { name: 'mocks', label: 'Mock服务', closable: true },
  cases: { name: 'cases', label: '用例管理', closable: true },
  'ui-cases': { name: 'ui-cases', label: '用例管理', closable: true },
  'ui-reports': { name: 'ui-reports', label: 'UI测试报告', closable: true },
  execute: { name: 'execute', label: '测试计划', closable: true },
  reports: { name: 'reports', label: '报告中心', closable: true },
  ai_cases: { name: 'ai_cases', label: 'AI生成用例', closable: true },
  knowledge_projects: { name: 'knowledge_projects', label: '项目配置', closable: true },
  knowledge_bases: { name: 'knowledge_bases', label: '知识库配置', closable: true },
  knowledge_workflows: { name: 'knowledge_workflows', label: '工作流配置', closable: true },
  knowledge_qa: { name: 'knowledge_qa', label: '知识问答', closable: true },
  logs: { name: 'logs', label: '日志中心', closable: true },
  accounts: { name: 'accounts', label: '用户管理', closable: true },
  roles: { name: 'roles', label: '角色管理', closable: true },
  tickets: { name: 'tickets', label: '工单管理', closable: true },
  api_key_configs: { name: 'api_key_configs', label: 'API Key配置', closable: true }
}

const menuTree: MenuNode[] = [
  {
    key: 'interface-test',
    label: '接口测试',
    icon: ApiOutlined,
    children: [
      { key: 'dashboard', label: menuMeta.dashboard.label, icon: DashboardOutlined },
      { key: 'projects', label: menuMeta.projects.label, icon: ProjectOutlined },
      { key: 'environments', label: menuMeta.environments.label, icon: CloudServerOutlined },
      { key: 'apis', label: menuMeta.apis.label, icon: ApiOutlined },
      { key: 'mocks', label: menuMeta.mocks.label, icon: ExperimentOutlined },
      { key: 'cases', label: menuMeta.cases.label, icon: FileTextOutlined },
      { key: 'execute', label: menuMeta.execute.label, icon: PlayCircleOutlined },
      { key: 'reports', label: menuMeta.reports.label, icon: BarChartOutlined },
      { key: 'logs', label: menuMeta.logs.label, icon: ProfileOutlined }
    ]
  },
  {
    key: 'ui-tests',
    label: 'UI测试',
    icon: DesktopOutlined,
    children: [
      { key: 'ui-cases', label: menuMeta['ui-cases'].label, icon: FileTextOutlined },
      { key: 'ui-reports', label: menuMeta['ui-reports'].label, icon: BarChartOutlined }
    ]
  },
  { key: 'ai_cases', label: menuMeta.ai_cases.label, icon: CheckCircleOutlined },
  {
    key: 'knowledge',
    label: '知识库',
    icon: FileTextOutlined,
    children: [
      { key: 'knowledge_projects', label: menuMeta.knowledge_projects.label, icon: ProjectOutlined },
      { key: 'knowledge_bases', label: menuMeta.knowledge_bases.label, icon: FileTextOutlined },
      { key: 'knowledge_workflows', label: menuMeta.knowledge_workflows.label, icon: PlayCircleOutlined },
      { key: 'knowledge_qa', label: menuMeta.knowledge_qa.label, icon: CheckCircleOutlined }
    ]
  },
  {
    key: 'system',
    label: '系统管理',
    icon: SettingOutlined,
    children: [
      { key: 'accounts', label: menuMeta.accounts.label, icon: TeamOutlined },
      { key: 'roles', label: menuMeta.roles.label, icon: SettingOutlined },
      { key: 'tickets', label: menuMeta.tickets.label, icon: FileTextOutlined },
      { key: 'api_key_configs', label: menuMeta.api_key_configs.label, icon: LockOutlined }
    ]
  }
]

function restoreTabs(): AppTab[] {
  try {
    const raw = JSON.parse(localStorage.getItem('opened_tabs') || '[]')
    if (Array.isArray(raw)) {
      const restored = raw
        .map((tab: any) => menuMeta[tab?.name === 'ui-tests' ? 'ui-cases' : tab?.name])
        .filter(Boolean)
      const unique = Array.from(new Map(restored.map(tab => [tab.name, tab])).values())
      if (unique.length > 0) {
        return unique.some(tab => tab.name === 'dashboard') ? unique : [menuMeta.dashboard, ...unique]
      }
    }
  } catch {}
  return [menuMeta.dashboard]
}

function restoreActive(tabs: AppTab[]) {
  const savedMenu = localStorage.getItem('active_menu') || 'dashboard'
  const saved = savedMenu === 'ui-tests' ? 'ui-cases' : savedMenu
  return tabs.some(tab => tab.name === saved) ? saved : 'dashboard'
}

const openedTabs = ref<AppTab[]>(restoreTabs())
const active = ref(restoreActive(openedTabs.value))
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)
const isMobile = ref(false)
const loginLoading = ref(false)

const me = ref<User | null>(null)
const sessionExpired = ref(false)
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const users = ref<any[]>([])
const roles = ref<any[]>([])
const roleMenus = ref<any[]>([])
const projects = ref<any[]>([])
const projectList = ref<any[]>([])
const environments = ref<any[]>([])
const environmentList = ref<any[]>([])
const apis = ref<any[]>([])
const apiList = ref<any[]>([])
const mockList = ref<any[]>([])
const uiCaseList = ref<any[]>([])
const cases = ref<any[]>([])
const caseList = ref<any[]>([])
const executions = ref<any[]>([])
const reportList = ref<any[]>([])
const uiReportList = ref<any[]>([])
const planList = ref<any[]>([])
const selectedPlanIds = ref<number[]>([])
const batchExecutingPlans = ref(false)
const logs = ref<any[]>([])
const operationLogs = ref<any[]>([])
const executionLogs = ref<any[]>([])
const exceptionLogs = ref<any[]>([])
const selectedProject = ref<any>(null)

const loginForm = reactive({ username: '', password: '' })
const userSearch = reactive({ username: '', status: '' })
const userPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const roleSearch = reactive({ name: '', status: '' })
const rolePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const projectSearch = reactive({ name: '' })
const projectPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const environmentSearch = reactive({ project_id: undefined as number | undefined, name: '' })
const environmentPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const apiSearch = reactive({ project_id: undefined as number | undefined, name: '', url: '' })
const apiPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const mockSearch = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, name: '', path: '', status: '' })
const mockPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const uiCaseSearch = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, name: '', status: '' })
const uiCasePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const caseSearch = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined })
const casePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const planSearch = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '' })
const planPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const reportSearch = reactive({ name: '', status: '' })
const reportPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const uiReportSearch = reactive({ name: '', status: '' })
const uiReportPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const aiGenerationPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const knowledgeProjectSearch = reactive({ name: '', status: '' })
const knowledgeProjectPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const knowledgeSearch = reactive({ project_id: undefined as number | undefined, name: '', status: '' })
const knowledgePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const knowledgeDocumentSearch = reactive({ keyword: '', status: '' })
const knowledgeDocumentPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const knowledgeWorkflowSearch = reactive({ name: '', status: '' })
const knowledgeWorkflowPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const qaSessionSearch = reactive({ project_id: undefined as number | undefined })
const ticketSearch = reactive({ title: '', category: '', status: '' })
const apiKeyConfigSearch = reactive({ keyword: '', status: '' })
const ticketPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const apiKeyConfigPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const selectedReportIds = ref<number[]>([])
const selectedUiReportIds = ref<number[]>([])
const aiGenerations = ref<any[]>([])
const knowledgeProjects = ref<any[]>([])
const knowledgeProjectList = ref<any[]>([])
const knowledgeBases = ref<any[]>([])
const knowledgeDocuments = ref<any[]>([])
const difyDatasets = ref<any[]>([])
const knowledgeWorkflows = ref<any[]>([])
const knowledgeWorkflowList = ref<any[]>([])
const qaSessions = ref<any[]>([])
const qaMessages = ref<any[]>([])
const tickets = ref<any[]>([])
const apiKeyConfigs = ref<any[]>([])
const apiKeyConfigList = ref<any[]>([])
const workflowApiKeyOptions = ref<any[]>([])
const aiSourceFiles = ref<any[]>([])
const aiLastUploadedFilename = ref('')
const aiGenerating = ref(false)
let aiGenerationPoller: number | undefined
const activeLogTab = ref('operations')
const operationLogSearch = reactive({ module: '', action: '', result: '', start_time: '', end_time: '' })
const executionLogSearch = reactive({ name: '', status: '' })
const exceptionLogSearch = reactive({ name: '', status: '' })
const operationLogPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const executionLogPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const exceptionLogPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const planExecutionPollers = new Map<number, number>()
const createUserDialogVisible = ref(false)
const editUserDialogVisible = ref(false)
const createRoleDialogVisible = ref(false)
const editRoleDialogVisible = ref(false)
const rolePermissionDialogVisible = ref(false)
const createTicketVisible = ref(false)
const ticketDetailVisible = ref(false)
const processTicketVisible = ref(false)
const apiKeyConfigFormVisible = ref(false)
const knowledgeFormVisible = ref(false)
const knowledgeProjectFormVisible = ref(false)
const knowledgeDocumentsVisible = ref(false)
const knowledgeRetrieveVisible = ref(false)
const knowledgeDocumentsLoading = ref(false)
const knowledgeChecking = ref(false)
const difyDatasetsLoading = ref(false)
const knowledgeRetrieving = ref(false)
const knowledgeRetrieved = ref(false)
const knowledgeWorkflowFormVisible = ref(false)
const qaSessionFormVisible = ref(false)
const knowledgeWorkflowCheckingId = ref<number | null>(null)
const qaAsking = ref(false)
const createProjectDialogVisible = ref(false)
const editProjectDialogVisible = ref(false)
const createEnvironmentDialogVisible = ref(false)
const editEnvironmentDialogVisible = ref(false)
const createMockDialogVisible = ref(false)
const editMockDialogVisible = ref(false)
const createUiCaseDialogVisible = ref(false)
const editUiCaseDialogVisible = ref(false)
const aiStepDialogVisible = ref(false)
const uiPickerDialogVisible = ref(false)
const uiExecutionDetailVisible = ref(false)
const aiSettingDialogVisible = ref(false)
const aiSettingTesting = ref(false)
const changePasswordDialogVisible = ref(false)
const caseBodyDialogVisible = ref(false)
const caseDetailDialogVisible = ref(false)
const executionDetailDialogVisible = ref(false)
const operationLogDetailVisible = ref(false)
const executionLogDetailVisible = ref(false)
const caseBodyPreview = ref('')
const caseDetail = reactive<any>({})
const executionDetail = reactive<any>({ task: null, results: [] })
const uiExecutionDetail = reactive<any>({ task: null, results: [] })
const uiArtifactObjectUrls = reactive<Record<string, string>>({})
const uiArtifactLoading = new Set<string>()
const uiArtifactFailed = new Set<string>()
const aiSettings = ref<any[]>([])
const uiExecutionDetailTime = computed(() => {
  const task = uiExecutionDetail.task || {}
  const started = task.started_at || task.create_date || ''
  const ended = task.ended_at || task.update_date || ''
  if (started && ended && started !== ended) return `${started} 至 ${ended}`
  return started || ended || '-'
})
const currentUiExecutionError = computed(() => {
  const summary = uiExecutionDetail.task?.summary || {}
  if (summary.error) return String(summary.error)
  if (summary.message && ['failed', 'error', 'stopped'].includes(String(summary.status || uiExecutionDetail.task?.status || ''))) {
    return String(summary.message)
  }
  for (const result of uiExecutionDetail.results || []) {
    const message = uiResultErrorMessage(result)
    if (message) return message
  }
  return ''
})
const uiPicker = reactive({
  sessionId: '',
  status: '',
  statusText: '未启动',
  message: '',
  xpath: '',
  summaryText: '',
  lastPickKey: '',
  pendingResult: null as any,
  targetRow: null as UiStepRow | null,
  targetForm: null as UiCaseFormState | null,
  mode: 'operate',
  recordAction: 'click' as UiRecordAction,
  recordActionAuto: true,
  inputText: '',
  screenshotUrl: '',
  viewportWidth: 1366,
  viewportHeight: 1050,
  zoomPercent: 100,
  loading: false
})
const aiStepGenerator = reactive({
  targetForm: null as UiCaseFormState | null,
  prompt: '',
  mode: 'append' as 'append' | 'replace',
  generatedSteps: [] as UiStepRow[],
  loading: false
})
const uiStepDrag = reactive({
  form: null as UiCaseFormState | null,
  index: -1
})
let uiPickerTimer: number | undefined
const operationLogDetail = ref<any>(null)
const executionLogDetail = ref<any>(null)
const userForm = reactive({ username: '', real_name: '', role: 'tester' })
const editUserForm = reactive({ id: undefined as number | undefined, username: '', real_name: '', role: 'tester' })
const roleForm = reactive({ code: '', name: '', description: '', status: 'active', menus: [] as string[] })
const editRoleForm = reactive({ id: undefined as number | undefined, code: '', name: '', description: '', status: 'active', menus: [] as string[], is_builtin: false })
const rolePermissionForm = reactive({ id: undefined as number | undefined, name: '', description: '', status: 'active', menus: [] as string[] })
const ticketForm = reactive({ category: 'feature', title: '', content: '', files: [] as any[] })
const ticketProcessForm = reactive({ status: 'processing', reply: '' })
const apiKeyConfigForm = reactive({ id: undefined as number | undefined, env_key: '', display_name: '', status: 'active', description: '' })
const ticketDetail = ref<any>(null)
const ticketSubmitting = ref(false)
const selectedKnowledgeBase = ref<any>(null)
const knowledgeProjectForm = reactive({ id: undefined as number | undefined, name: '', description: '', status: 'active' })
const knowledgeForm = reactive({ id: undefined as number | undefined, project_id: undefined as number | undefined, name: '', dify_dataset_id: '', status: 'active', description: '' })
const knowledgeRetrieveForm = reactive({ query: '', top_k: 5, score_threshold: undefined as number | undefined })
const knowledgeRetrieveResult = ref<any[]>([])
const selectedQaSession = ref<any>(null)
const knowledgeWorkflowForm = reactive({ id: undefined as number | undefined, name: '', api_base_url: '', api_key_env: '', status: 'active', description: '' })
const qaSessionForm = reactive({ project_id: undefined as number | undefined, workflow_id: undefined as number | undefined, title: '' })
const qaQuestion = ref('')
const changePasswordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const projectForm = reactive({ name: '', description: '' })
const editProjectForm = reactive({ id: undefined as number | undefined, name: '', description: '' })
const envForm = reactive({ project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const editEnvironmentForm = reactive({ id: undefined as number | undefined, project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const mockForm = reactive<MockFormState>({
  id: undefined,
  project_id: undefined,
  environment_id: undefined,
  name: '',
  method: 'GET',
  path: '',
  status: 'active',
  status_code: '200',
  delay_ms: '0',
  headerRows: [],
  response_body: '{\n  "code": 0,\n  "message": "success"\n}',
  body_format: 'json',
  sm3_enabled: false,
  description: ''
})
const editMockForm = reactive<MockFormState>({
  id: undefined,
  project_id: undefined,
  environment_id: undefined,
  name: '',
  method: 'GET',
  path: '',
  status: 'active',
  status_code: '200',
  delay_ms: '0',
  headerRows: [],
  response_body: '',
  body_format: 'json',
  sm3_enabled: false,
  description: ''
})
const uiCaseForm = reactive<UiCaseFormState>({
  id: undefined,
  project_id: undefined,
  environment_id: undefined,
  name: '',
  start_url: '/',
  description: '',
  execution_mode: 'ai',
  test_goal: '',
  test_data_text: '{}',
  assertion_goal: '',
  max_steps: 30,
  step_timeout_ms: 10000,
  allow_ai_actions: true,
  status: 'active',
  browser_channel: 'chromium',
  headless: true,
  wait_until: 'networkidle',
  wait_after_load_ms: 500,
  steps: []
})
const editUiCaseForm = reactive<UiCaseFormState>({
  id: undefined,
  project_id: undefined,
  environment_id: undefined,
  name: '',
  start_url: '/',
  description: '',
  execution_mode: 'ai',
  test_goal: '',
  test_data_text: '{}',
  assertion_goal: '',
  max_steps: 30,
  step_timeout_ms: 10000,
  allow_ai_actions: true,
  status: 'active',
  browser_channel: 'chromium',
  headless: true,
  wait_until: 'networkidle',
  wait_after_load_ms: 500,
  steps: []
})
const aiSettingForm = reactive({
  id: undefined as number | undefined,
  name: '',
  provider_url: '',
  model_name: '',
  api_key: '',
  status: 'disabled',
  is_default: false,
  description: ''
})
const caseForm = reactive({
  id: undefined as number | undefined,
  project_id: undefined as number | undefined,
  api_id: undefined as number | undefined,
  name: '',
  description: '',
  bodyText: '{}',
  bodyFormat: 'json' as ApiEditor['bodyFormat'],
  assertionRows: [] as CaseAssertionRow[],
  extractorRows: [] as CaseExtractorRow[]
})
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })
const apiEditors = reactive<Record<string, ApiEditor>>({})
const planEditors = reactive<Record<string, PlanEditor>>({})
const UI_CASE_CREATE_TAB = 'ui-case-create'
const UI_CASE_EDIT_PREFIX = 'ui-case-edit-'
const avatarText = computed(() => me.value?.username.slice(0, 1).toUpperCase() || 'U')
const activeApiEditor = computed(() => apiEditors[active.value])
const activePlanEditor = computed(() => planEditors[active.value])
const activeUiCaseEditor = computed(() => {
  if (active.value === UI_CASE_CREATE_TAB) {
    return { label: '新增UI用例', form: uiCaseForm, mode: 'create' as const, tabName: UI_CASE_CREATE_TAB }
  }
  if (active.value.startsWith(UI_CASE_EDIT_PREFIX) && editUiCaseForm.id) {
    return { label: `编辑UI用例：${editUiCaseForm.name || editUiCaseForm.id}`, form: editUiCaseForm, mode: 'edit' as const, tabName: active.value }
  }
  return null
})
const uiPickerSteps = computed(() => uiPicker.targetForm?.steps || [])
const uiPickerSelectOptions = computed(() => {
  const options = uiPicker.pendingResult?.summary?.options
  if (!Array.isArray(options)) return []
  return options
    .map((option: any, index: number) => {
      const rawValue = sanitizeUiOptionText(option?.value ?? option?.text ?? option?.name ?? '')
      const rawLabel = sanitizeUiOptionText(option?.label ?? option?.text ?? option?.name ?? '')
      const originalValue = rawValue || rawLabel
      const label = rawLabel || rawValue || `选项${index + 1}`
      const value = originalValue || label
      return {
        key: `${index}-${value || label || 'empty'}`,
        value,
        label: label || value || `选项${index + 1}`,
        originalValue,
        selected: !!option?.selected
      }
    })
    .filter(option => isValidUiOptionText(option.value) || isValidUiOptionText(option.label))
})
const canAppendRecordedUiStep = computed(() => {
  if (!uiPicker.pendingResult) return false
  const action = uiPicker.recordActionAuto ? inferUiRecordAction(uiPicker.pendingResult) : uiPicker.recordAction
  if (['select', 'fill', 'assert_text'].includes(action)) return !!uiPicker.inputText.trim()
  return true
})
const uiPickerImageStyle = computed(() => ({
  width: `${Math.round(uiPicker.viewportWidth * uiPicker.zoomPercent / 100)}px`,
  height: 'auto',
  maxWidth: 'none',
  maxHeight: 'none'
}))
const currentPageTitle = computed(() => activeApiEditor.value?.label || activePlanEditor.value?.label || activeUiCaseEditor.value?.label || menuMeta[active.value]?.label || '接口测试平台')
const roleMenuTreeData = computed(() => roleMenus.value.map(group => ({
  key: group.key,
  title: group.label,
  children: group.children?.map((child: any) => ({ key: child.key, title: child.label }))
})))
const roleMenuLeafKeys = computed(() => new Set(roleMenus.value.flatMap(group => group.children?.map((child: any) => child.key) || [group.key])))
const permittedMenuKeys = computed(() => {
  const keys = me.value?.menus?.length ? me.value.menus : Object.keys(menuMeta)
  const normalized = new Set(keys)
  if (normalized.has('ui-tests')) {
    normalized.add('ui-cases')
    normalized.add('ui-reports')
  }
  return normalized
})
const visibleMenuGroups = computed(() => menuTree
  .map(item => {
    if (!item.children) return permittedMenuKeys.value.has(item.key) ? item : null
    const children = item.children.filter(child => permittedMenuKeys.value.has(child.key))
    return children.length ? { ...item, children } : null
  })
  .filter(Boolean) as MenuNode[])

function isMenuAllowed(key: string) {
  return Boolean(menuMeta[key] && permittedMenuKeys.value.has(key))
}

function syncAllowedTabs() {
  const fallback = permittedMenuKeys.value.has('dashboard') ? menuMeta.dashboard : menuMeta[[...permittedMenuKeys.value].find(key => menuMeta[key]) || 'dashboard']
  openedTabs.value = openedTabs.value.filter(tab => isMenuAllowed(tab.name))
  if (openedTabs.value.length === 0 && fallback) openedTabs.value = [fallback]
  if (!isMenuAllowed(active.value)) active.value = openedTabs.value[0]?.name || fallback?.name || 'dashboard'
  saveTabs()
}
const dashboardStats = computed(() => [
  { label: '项目数', value: projects.value.length, description: '已配置项目', tone: 'blue', icon: ProjectOutlined },
  { label: '接口数', value: apis.value.length, description: '已维护接口定义', tone: 'cyan', icon: ApiOutlined },
  { label: '用例数', value: cases.value.length, description: '可用于回归执行', tone: 'green', icon: FileTextOutlined },
  { label: '执行任务', value: executions.value.length, description: '历史执行任务', tone: 'orange', icon: PlayCircleOutlined }
])
const activeKnowledgeProjects = computed(() => knowledgeProjects.value.filter(item => item.status === 'active'))
const activeKnowledgeWorkflows = computed(() => knowledgeWorkflows.value.filter(item => item.status === 'active'))
const qaSessionWorkflows = computed(() => activeKnowledgeWorkflows.value)
const caseSearchApis = computed(() => apis.value.filter(item => caseSearch.project_id && item.project_id === caseSearch.project_id))
const caseFormApis = computed(() => apis.value.filter(item => caseForm.project_id && item.project_id === caseForm.project_id))
const currentCaseApi = computed(() => selectedCaseApi())
const caseBodyFormatLabel = computed(() => {
  const labels: Record<string, string> = {
    json: 'JSON',
    xml: 'XML',
    'x-www-form-data': 'x-www-form-data'
  }
  return labels[caseForm.bodyFormat] || 'JSON'
})
const caseBodySm3Hint = computed(() => currentCaseApi.value?.encryption?.sm3_signature ? '，该接口已开启SM3签名' : '')
const caseBodyPlaceholder = computed(() => {
  if (caseForm.bodyFormat === 'xml') return '<request>\\n  <token>${token}</token>\\n</request>'
  if (caseForm.bodyFormat === 'x-www-form-data') return '{\\n  "username": "admin",\\n  "password": "123456"\\n}'
  return '{\\n  "token": "${token}"\\n}'
})
const caseBodyHelpText = computed(() => {
  if (caseForm.bodyFormat === 'xml') return '当前接口 Body 格式为 XML，保存时会按文本发送。'
  if (caseForm.bodyFormat === 'x-www-form-data') return '当前接口 Body 格式为表单，第一版请用 JSON 对象维护表单键值。'
  return '当前接口 Body 格式为 JSON，保存前会校验 JSON 合法性。'
})
const planSearchApis = computed(() => apis.value.filter(item => planSearch.project_id && item.project_id === planSearch.project_id))
const mockSearchEnvironments = computed(() => environments.value.filter(item => mockSearch.project_id && item.project_id === mockSearch.project_id))
const mockFormEnvironments = computed(() => environments.value.filter(item => mockForm.project_id && item.project_id === mockForm.project_id))
const editMockFormEnvironments = computed(() => environments.value.filter(item => editMockForm.project_id && item.project_id === editMockForm.project_id))
const uiCaseSearchEnvironments = computed(() => environments.value.filter(item => uiCaseSearch.project_id && item.project_id === uiCaseSearch.project_id))
const uiCaseFormEnvironments = computed(() => environments.value.filter(item => uiCaseForm.project_id && item.project_id === uiCaseForm.project_id))
const editUiCaseFormEnvironments = computed(() => environments.value.filter(item => editUiCaseForm.project_id && item.project_id === editUiCaseForm.project_id))
const assertionTargets = [
  { label: 'HTTP状态码', value: 'status' },
  { label: '响应时间', value: 'duration' },
  { label: 'JSONPath', value: 'jsonpath' },
  { label: 'XMLPath', value: 'xmlpath' },
  { label: '响应文本', value: 'text' }
]
const assertionChecks = {
  status: [{ label: '等于', value: 'equal' }],
  duration: [{ label: '小于', value: 'lt' }],
  jsonpath: [
    { label: '等于', value: 'equal' },
    { label: '存在', value: 'exists' },
    { label: '非空', value: 'not_empty' }
  ],
  xmlpath: [
    { label: '等于', value: 'equal' },
    { label: '存在', value: 'exists' },
    { label: '非空', value: 'not_empty' }
  ],
  text: [{ label: '包含', value: 'contains' }]
} as const
const extractorTypes = [
  { label: 'JSONPath', value: 'jsonpath' },
  { label: 'XMLPath', value: 'xmlpath' },
  { label: '正则表达式', value: 'regex' }
]
const paginationTotal = (total: number) => `共 ${total} 条`

function parseJson(text: string, fallback: any) {
  try { return JSON.parse(text || '') } catch { return fallback }
}

function quoteBareJsonVariables(text: string) {
  let result = ''
  let inString = false
  let escaped = false
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (inString) {
      result += char
      if (escaped) {
        escaped = false
      } else if (char === '\\') {
        escaped = true
      } else if (char === '"') {
        inString = false
      }
      continue
    }
    if (char === '"') {
      inString = true
      result += char
      continue
    }
    if (char === '$' && text[index + 1] === '{') {
      const end = text.indexOf('}', index + 2)
      if (end !== -1) {
        result += JSON.stringify(text.slice(index, end + 1))
        index = end
        continue
      }
    }
    result += char
  }
  return result
}

function parseJsonAllowVariables(text: string, fallback: any) {
  try {
    return JSON.parse(text || '')
  } catch {
    try {
      return JSON.parse(quoteBareJsonVariables(text || ''))
    } catch {
      return fallback
    }
  }
}

async function loadAll() {
  const calls = [
    api.get('/projects').then(r => projects.value = r.data),
    api.get('/environments').then(r => environments.value = r.data),
    api.get('/apis').then(r => apis.value = r.data),
    refreshAllCases(),
    api.get('/executions').then(r => executions.value = r.data)
  ]
  calls.push(loadUsers())
  calls.push(loadRoles())
  calls.push(loadProjects())
  calls.push(loadEnvironments())
    calls.push(loadApis())
    calls.push(loadMocks())
    calls.push(loadUiCases())
    calls.push(loadAiSetting())
    calls.push(loadCases())
  calls.push(loadPlans())
  calls.push(loadReports())
  calls.push(loadUiReports())
  calls.push(loadAiGenerations())
  calls.push(loadKnowledgeProjects())
  calls.push(loadKnowledgeBases())
  calls.push(loadKnowledgeWorkflows())
  calls.push(loadQaSessions())
  calls.push(loadTickets())
  calls.push(loadApiKeyConfigs())
  calls.push(loadWorkflowApiKeyOptions())
  calls.push(loadLogs())
  await Promise.allSettled(calls)
}

async function loadUsers() {
  const username = userSearch.username.trim()
  const status = userSearch.status
  const { data } = await api.get('/users', {
    params: {
      ...(username ? { username } : {}),
      ...(status ? { status } : {}),
      page: userPagination.page,
      page_size: userPagination.pageSize
    }
  })
  users.value = data.items
  userPagination.total = data.total
  userPagination.page = data.page
  userPagination.pageSize = data.page_size
}

async function searchUsers() {
  userPagination.page = 1
  await loadUsers()
}

async function resetUserSearch() {
  userSearch.username = ''
  userSearch.status = ''
  userPagination.page = 1
  await loadUsers()
}

async function changeUserPage(page: number) {
  userPagination.page = page
  await loadUsers()
}

async function loadRoles() {
  const name = roleSearch.name.trim()
  const status = roleSearch.status
  const [roleRes, menuRes] = await Promise.all([
    api.get('/roles', {
      params: {
        ...(name ? { name } : {}),
        ...(status ? { status } : {}),
        page: rolePagination.page,
        page_size: rolePagination.pageSize
      }
    }),
    roleMenus.value.length ? Promise.resolve({ data: roleMenus.value }) : api.get('/roles/menus')
  ])
  roles.value = roleRes.data.items
  rolePagination.total = roleRes.data.total
  rolePagination.page = roleRes.data.page
  rolePagination.pageSize = roleRes.data.page_size
  roleMenus.value = menuRes.data
}

async function searchRoles() {
  rolePagination.page = 1
  await loadRoles()
}

async function resetRoleSearch() {
  roleSearch.name = ''
  roleSearch.status = ''
  rolePagination.page = 1
  await loadRoles()
}

async function changeRolePage(page: number) {
  rolePagination.page = page
  await loadRoles()
}

async function loadProjects() {
  const name = projectSearch.name.trim()
  const { data } = await api.get('/projects', {
    params: {
      ...(name ? { name } : {}),
      page: projectPagination.page,
      page_size: projectPagination.pageSize
    }
  })
  projectList.value = data.items
  projectPagination.total = data.total
  projectPagination.page = data.page
  projectPagination.pageSize = data.page_size
}

async function searchProjects() {
  projectPagination.page = 1
  await loadProjects()
}

async function resetProjectSearch() {
  projectSearch.name = ''
  projectPagination.page = 1
  await loadProjects()
}

async function changeProjectPage(page: number) {
  projectPagination.page = page
  await loadProjects()
}

async function loadEnvironments() {
  const name = environmentSearch.name.trim()
  const projectId = environmentSearch.project_id
  const { data } = await api.get('/environments', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(name ? { name } : {}),
      page: environmentPagination.page,
      page_size: environmentPagination.pageSize
    }
  })
  environmentList.value = data.items
  environmentPagination.total = data.total
  environmentPagination.page = data.page
  environmentPagination.pageSize = data.page_size
}

async function searchEnvironments() {
  environmentPagination.page = 1
  await loadEnvironments()
}

async function resetEnvironmentSearch() {
  environmentSearch.project_id = undefined
  environmentSearch.name = ''
  environmentPagination.page = 1
  await loadEnvironments()
}

async function changeEnvironmentPage(page: number) {
  environmentPagination.page = page
  await loadEnvironments()
}

async function loadApis() {
  const projectId = apiSearch.project_id
  const name = apiSearch.name.trim()
  const url = apiSearch.url.trim()
  const { data } = await api.get('/apis', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(name ? { name } : {}),
      ...(url ? { url } : {}),
      page: apiPagination.page,
      page_size: apiPagination.pageSize
    }
  })
  apiList.value = data.items
  apiPagination.total = data.total
  apiPagination.page = data.page
  apiPagination.pageSize = data.page_size
}

async function searchApis() {
  apiPagination.page = 1
  await loadApis()
}

async function resetApiSearch() {
  apiSearch.project_id = undefined
  apiSearch.name = ''
  apiSearch.url = ''
  apiPagination.page = 1
  await loadApis()
}

async function changeApiPage(page: number) {
  apiPagination.page = page
  await loadApis()
}

async function loadMocks() {
  const projectId = mockSearch.project_id
  const environmentId = mockSearch.environment_id
  const name = mockSearch.name.trim()
  const path = mockSearch.path.trim()
  const status = mockSearch.status
  const { data } = await api.get('/mocks', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(environmentId ? { environment_id: environmentId } : {}),
      ...(name ? { name } : {}),
      ...(path ? { path } : {}),
      ...(status ? { status } : {}),
      page: mockPagination.page,
      page_size: mockPagination.pageSize
    }
  })
  mockList.value = data.items
  mockPagination.total = data.total
  mockPagination.page = data.page
  mockPagination.pageSize = data.page_size
}

async function searchMocks() {
  mockPagination.page = 1
  await loadMocks()
}

async function resetMockSearch() {
  mockSearch.project_id = undefined
  mockSearch.environment_id = undefined
  mockSearch.name = ''
  mockSearch.path = ''
  mockSearch.status = ''
  mockPagination.page = 1
  await loadMocks()
}

function changeMockSearchProject() {
  mockSearch.environment_id = undefined
}

  async function changeMockPage(page: number) {
    mockPagination.page = page
    await loadMocks()
  }

  async function loadUiCases() {
    const projectId = uiCaseSearch.project_id
    const environmentId = uiCaseSearch.environment_id
    const name = uiCaseSearch.name.trim()
    const status = uiCaseSearch.status
    const { data } = await api.get('/ui-cases', {
      params: {
        ...(projectId ? { project_id: projectId } : {}),
        ...(environmentId ? { environment_id: environmentId } : {}),
        ...(name ? { name } : {}),
        ...(status ? { status } : {}),
        page: uiCasePagination.page,
        page_size: uiCasePagination.pageSize
      }
    })
    uiCaseList.value = data.items
    uiCasePagination.total = data.total
    uiCasePagination.page = data.page
    uiCasePagination.pageSize = data.page_size
  }

  async function searchUiCases() {
    uiCasePagination.page = 1
    await loadUiCases()
  }

  async function resetUiCaseSearch() {
    uiCaseSearch.project_id = undefined
    uiCaseSearch.environment_id = undefined
    uiCaseSearch.name = ''
    uiCaseSearch.status = ''
    uiCasePagination.page = 1
    await loadUiCases()
  }

  function changeUiCaseSearchProject() {
    uiCaseSearch.environment_id = undefined
  }

  async function changeUiCasePage(page: number) {
    uiCasePagination.page = page
    await loadUiCases()
  }
  
  async function loadCases() {
  const projectId = caseSearch.project_id
  const apiId = caseSearch.api_id
  const { data } = await api.get('/cases', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(apiId ? { api_id: apiId } : {}),
      page: casePagination.page,
      page_size: casePagination.pageSize
    }
  })
  caseList.value = data.items
  casePagination.total = data.total
  casePagination.page = data.page
  casePagination.pageSize = data.page_size
}

async function refreshAllCases() {
  const { data } = await api.get('/cases')
  cases.value = data
}

async function searchCases() {
  casePagination.page = 1
  await loadCases()
}

async function resetCaseSearch() {
  caseSearch.project_id = undefined
  caseSearch.api_id = undefined
  casePagination.page = 1
  await loadCases()
}

function changeCaseSearchProject() {
  caseSearch.api_id = undefined
}

async function changeCasePage(page: number) {
  casePagination.page = page
  await loadCases()
}

function caseSerialNumber(index: number) {
  return (casePagination.page - 1) * casePagination.pageSize + index + 1
}

async function loadPlans() {
  const projectId = planSearch.project_id
  const apiId = planSearch.api_id
  const name = planSearch.name.trim()
  const { data } = await api.get('/plans', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(apiId ? { api_id: apiId } : {}),
      ...(name ? { name } : {}),
      page: planPagination.page,
      page_size: planPagination.pageSize
    }
  })
  planList.value = data.items
  selectedPlanIds.value = selectedPlanIds.value.filter(id => planList.value.some(item => item.id === id))
  planPagination.total = data.total
  planPagination.page = data.page
  planPagination.pageSize = data.page_size
}

function changeSelectedPlans(keys: Array<string | number>) {
  selectedPlanIds.value = keys.map(key => Number(key)).filter(Boolean)
}

async function refreshPlansAfterChange() {
  await loadPlans()
}

async function searchPlans() {
  planPagination.page = 1
  await loadPlans()
}

async function resetPlanSearch() {
  planSearch.project_id = undefined
  planSearch.api_id = undefined
  planSearch.name = ''
  planPagination.page = 1
  await loadPlans()
}

function changePlanSearchProject() {
  planSearch.api_id = undefined
}

async function changePlanPage(page: number) {
  planPagination.page = page
  await loadPlans()
}

async function loadReports() {
  const name = reportSearch.name.trim()
  const status = reportSearch.status
  const { data } = await api.get('/executions', {
    params: {
      target_type: 'plan',
      ...(name ? { name } : {}),
      ...(status ? { status } : {}),
      page: reportPagination.page,
      page_size: reportPagination.pageSize
    }
  })
  reportList.value = data.items
  selectedReportIds.value = selectedReportIds.value.filter(id => reportList.value.some(item => item.id === id))
  reportPagination.total = data.total
  reportPagination.page = data.page
  reportPagination.pageSize = data.page_size
}

async function searchReports() {
  reportPagination.page = 1
  await loadReports()
}

async function resetReportSearch() {
  reportSearch.name = ''
  reportSearch.status = ''
  reportPagination.page = 1
  await loadReports()
}

async function changeReportPage(page: number) {
  reportPagination.page = page
  await loadReports()
}

async function loadUiReports() {
  const name = uiReportSearch.name.trim()
  const status = uiReportSearch.status
  const { data } = await api.get('/executions', {
    params: {
      target_type: 'ui_case',
      ...(name ? { name } : {}),
      ...(status ? { status } : {}),
      page: uiReportPagination.page,
      page_size: uiReportPagination.pageSize
    }
  })
  uiReportList.value = data.items
  selectedUiReportIds.value = selectedUiReportIds.value.filter(id => uiReportList.value.some(item => item.id === id))
  uiReportPagination.total = data.total
  uiReportPagination.page = data.page
  uiReportPagination.pageSize = data.page_size
}

async function searchUiReports() {
  uiReportPagination.page = 1
  await loadUiReports()
}

async function resetUiReportSearch() {
  uiReportSearch.name = ''
  uiReportSearch.status = ''
  uiReportPagination.page = 1
  await loadUiReports()
}

async function changeUiReportPage(page: number) {
  uiReportPagination.page = page
  await loadUiReports()
}

function aiGenerationSerialNumber(index: number) {
  return (aiGenerationPagination.page - 1) * aiGenerationPagination.pageSize + index + 1
}

function aiGenerationStatusText(status: string) {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '生成中',
    succeeded: '已完成',
    failed: '失败'
  }
  return labels[status] || status || '-'
}

function aiGenerationStatusColor(status: string) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'processing'
  return 'warning'
}

function clearAiGenerationPoller() {
  if (aiGenerationPoller !== undefined) {
    window.clearInterval(aiGenerationPoller)
    aiGenerationPoller = undefined
  }
}

function refreshAiGenerationPoller() {
  const needsPolling = aiGenerations.value.some(row => ['queued', 'running'].includes(row.status))
  if (needsPolling && aiGenerationPoller === undefined) {
    aiGenerationPoller = window.setInterval(() => void loadAiGenerations(true), 3000)
  }
  if (!needsPolling) clearAiGenerationPoller()
}

async function loadAiGenerations(isBackground = false) {
  const { data } = await api.get('/ai-case-generations', {
    params: { page: aiGenerationPagination.page, page_size: aiGenerationPagination.pageSize },
    headers: isBackground ? { 'X-Session-Activity': '0' } : undefined
  })
  aiGenerations.value = data.items
  aiGenerationPagination.total = data.total
  aiGenerationPagination.page = data.page
  aiGenerationPagination.pageSize = data.page_size
  refreshAiGenerationPoller()
}

async function changeAiGenerationPage(page: number) {
  aiGenerationPagination.page = page
  await loadAiGenerations()
}

function knowledgeProjectSerialNumber(index: number) {
  return (knowledgeProjectPagination.page - 1) * knowledgeProjectPagination.pageSize + index + 1
}

async function loadKnowledgeProjects() {
  const name = knowledgeProjectSearch.name.trim()
  const status = knowledgeProjectSearch.status
  const [listRes, allRes] = await Promise.all([
    api.get('/knowledge-projects', {
      params: {
        ...(name ? { name } : {}),
        ...(status ? { status } : {}),
        page: knowledgeProjectPagination.page,
        page_size: knowledgeProjectPagination.pageSize
      }
    }),
    api.get('/knowledge-projects')
  ])
  knowledgeProjectList.value = listRes.data.items
  knowledgeProjectPagination.total = listRes.data.total
  knowledgeProjectPagination.page = listRes.data.page
  knowledgeProjectPagination.pageSize = listRes.data.page_size
  knowledgeProjects.value = allRes.data
}

async function searchKnowledgeProjects() {
  knowledgeProjectPagination.page = 1
  await loadKnowledgeProjects()
}

async function resetKnowledgeProjectSearch() {
  knowledgeProjectSearch.name = ''
  knowledgeProjectSearch.status = ''
  knowledgeProjectPagination.page = 1
  await loadKnowledgeProjects()
}

async function changeKnowledgeProjectPage(page: number) {
  knowledgeProjectPagination.page = page
  await loadKnowledgeProjects()
}

async function loadDifyDatasets() {
  if (difyDatasetsLoading.value || difyDatasets.value.length) return
  difyDatasetsLoading.value = true
  try {
    const { data } = await api.get('/knowledge-bases/dify-datasets', { params: { page: 1, page_size: 100 } })
    difyDatasets.value = data.items || []
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Dify 知识库列表加载失败')
  } finally {
    difyDatasetsLoading.value = false
  }
}

function filterDifyDatasetOption(input: string, option: any) {
  return String(option?.title || option?.children || '').toLowerCase().includes(input.toLowerCase())
}

function handleDifyDatasetDropdown(visible: boolean) {
  if (visible) void loadDifyDatasets()
}

function changeDifyDataset(datasetId: string) {
  const dataset = difyDatasets.value.find(item => item.id === datasetId)
  if (dataset?.name && !knowledgeForm.name.trim()) {
    knowledgeForm.name = dataset.name
  }
}

function resetKnowledgeProjectForm() {
  knowledgeProjectForm.id = undefined
  knowledgeProjectForm.name = ''
  knowledgeProjectForm.description = ''
  knowledgeProjectForm.status = 'active'
}

function openCreateKnowledgeProject() {
  resetKnowledgeProjectForm()
  knowledgeProjectFormVisible.value = true
}

function openEditKnowledgeProject(row: any) {
  knowledgeProjectForm.id = row.id
  knowledgeProjectForm.name = row.name
  knowledgeProjectForm.description = row.description || ''
  knowledgeProjectForm.status = row.status || 'active'
  knowledgeProjectFormVisible.value = true
}

async function saveKnowledgeProject() {
  const name = knowledgeProjectForm.name.trim()
  if (!name) { message.warning('请输入项目名称'); return }
  const payload = { name, description: knowledgeProjectForm.description.trim(), status: knowledgeProjectForm.status }
  try {
    if (knowledgeProjectForm.id) {
      await api.put(`/knowledge-projects/${knowledgeProjectForm.id}`, payload)
      message.success('知识库项目已更新')
    } else {
      await api.post('/knowledge-projects', payload)
      knowledgeProjectPagination.page = 1
      message.success('知识库项目已创建')
    }
    knowledgeProjectFormVisible.value = false
    await loadKnowledgeProjects()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库项目保存失败')
  }
}

async function deleteKnowledgeProject(row: any) {
  try {
    await confirmAction(`确认删除知识库项目「${row.name}」？`, '删除知识库项目', { confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await api.delete(`/knowledge-projects/${row.id}`)
    if (knowledgeProjectList.value.length === 1 && knowledgeProjectPagination.page > 1) knowledgeProjectPagination.page -= 1
    await loadKnowledgeProjects()
    await loadKnowledgeBases()
    message.success('知识库项目已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库项目删除失败')
  }
}

function knowledgeSerialNumber(index: number) {
  return (knowledgePagination.page - 1) * knowledgePagination.pageSize + index + 1
}

function maskDatasetId(value: string) {
  if (!value) return '-'
  if (value.length <= 12) return value
  return `${value.slice(0, 8)}***${value.slice(-6)}`
}

async function loadKnowledgeBases() {
  const { data } = await api.get('/knowledge-bases', {
    params: {
      ...(knowledgeSearch.project_id ? { project_id: knowledgeSearch.project_id } : {}),
      ...(knowledgeSearch.name.trim() ? { name: knowledgeSearch.name.trim() } : {}),
      ...(knowledgeSearch.status ? { status: knowledgeSearch.status } : {}),
      page: knowledgePagination.page,
      page_size: knowledgePagination.pageSize
    }
  })
  knowledgeBases.value = data.items
  knowledgePagination.total = data.total
  knowledgePagination.page = data.page
  knowledgePagination.pageSize = data.page_size
}

async function searchKnowledgeBases() {
  knowledgePagination.page = 1
  await loadKnowledgeBases()
}

async function resetKnowledgeSearch() {
  knowledgeSearch.project_id = undefined
  knowledgeSearch.name = ''
  knowledgeSearch.status = ''
  knowledgePagination.page = 1
  await loadKnowledgeBases()
}

async function changeKnowledgePage(page: number) {
  knowledgePagination.page = page
  await loadKnowledgeBases()
}

function resetKnowledgeForm() {
  knowledgeForm.id = undefined
  knowledgeForm.project_id = undefined
  knowledgeForm.name = ''
  knowledgeForm.dify_dataset_id = ''
  knowledgeForm.status = 'active'
  knowledgeForm.description = ''
  knowledgeChecking.value = false
}

function openCreateKnowledgeBase() {
  resetKnowledgeForm()
  knowledgeFormVisible.value = true
  void loadDifyDatasets()
}

function openEditKnowledgeBase(row: any) {
  knowledgeForm.id = row.id
  knowledgeForm.project_id = row.project_id
  knowledgeForm.name = row.name
  knowledgeForm.dify_dataset_id = row.dify_dataset_id
  knowledgeForm.status = row.status || 'active'
  knowledgeForm.description = row.description || ''
  knowledgeFormVisible.value = true
  void loadDifyDatasets()
}

function validateKnowledgeForm() {
  if (!knowledgeForm.project_id) { message.warning('请选择项目'); return false }
  if (!knowledgeForm.name.trim()) { message.warning('请输入知识库名称'); return false }
  if (!knowledgeForm.dify_dataset_id.trim()) { message.warning('请输入 Dify Dataset ID'); return false }
  return true
}

async function checkKnowledgeForm() {
  if (!knowledgeForm.dify_dataset_id.trim()) { message.warning('请输入 Dify Dataset ID'); return }
  knowledgeChecking.value = true
  try {
    const { data } = await api.post('/knowledge-bases/check', { dify_dataset_id: knowledgeForm.dify_dataset_id.trim() })
    message.success(`连接成功，文档数：${data.document_count ?? 0}`)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Dify 知识库连接失败')
  } finally {
    knowledgeChecking.value = false
  }
}

async function saveKnowledgeBase() {
  if (!validateKnowledgeForm()) return
  const payload = {
    project_id: knowledgeForm.project_id,
    name: knowledgeForm.name.trim(),
    dify_dataset_id: knowledgeForm.dify_dataset_id.trim(),
    status: knowledgeForm.status,
    description: knowledgeForm.description.trim()
  }
  try {
    if (knowledgeForm.id) {
      await api.put(`/knowledge-bases/${knowledgeForm.id}`, payload)
      message.success('知识库绑定已更新')
    } else {
      await api.post('/knowledge-bases', payload)
      knowledgePagination.page = 1
      message.success('知识库绑定已创建')
    }
    knowledgeFormVisible.value = false
    await loadKnowledgeProjects()
    await loadKnowledgeBases()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库绑定保存失败')
  }
}

async function checkKnowledgeBase(row: any) {
  try {
    const { data } = await api.post(`/knowledge-bases/${row.id}/check`)
    message.success(`连接成功，文档数：${data.document_count ?? 0}`)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Dify 知识库连接失败')
  }
}

async function deleteKnowledgeBase(row: any) {
  try {
    await confirmAction(`确认删除知识库绑定「${row.name}」？不会删除 Dify 侧知识库。`, '删除知识库绑定', { confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await api.delete(`/knowledge-bases/${row.id}`)
    if (knowledgeBases.value.length === 1 && knowledgePagination.page > 1) knowledgePagination.page -= 1
    await loadKnowledgeBases()
    message.success('知识库绑定已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库绑定删除失败')
  }
}

async function loadKnowledgeDocuments() {
  if (!selectedKnowledgeBase.value) return
  knowledgeDocumentsLoading.value = true
  try {
    const { data } = await api.get(`/knowledge-bases/${selectedKnowledgeBase.value.id}/documents`, {
      params: {
        ...(knowledgeDocumentSearch.keyword.trim() ? { keyword: knowledgeDocumentSearch.keyword.trim() } : {}),
        ...(knowledgeDocumentSearch.status.trim() ? { status: knowledgeDocumentSearch.status.trim() } : {}),
        page: knowledgeDocumentPagination.page,
        page_size: knowledgeDocumentPagination.pageSize
      }
    })
    knowledgeDocuments.value = data.items
    knowledgeDocumentPagination.total = data.total
    knowledgeDocumentPagination.page = data.page
    knowledgeDocumentPagination.pageSize = data.page_size
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库文档加载失败')
  } finally {
    knowledgeDocumentsLoading.value = false
  }
}

async function openKnowledgeDocuments(row: any) {
  selectedKnowledgeBase.value = row
  knowledgeDocumentSearch.keyword = ''
  knowledgeDocumentSearch.status = ''
  knowledgeDocumentPagination.page = 1
  knowledgeDocuments.value = []
  knowledgeDocumentsVisible.value = true
  await loadKnowledgeDocuments()
}

async function searchKnowledgeDocuments() {
  knowledgeDocumentPagination.page = 1
  await loadKnowledgeDocuments()
}

async function resetKnowledgeDocuments() {
  knowledgeDocumentSearch.keyword = ''
  knowledgeDocumentSearch.status = ''
  knowledgeDocumentPagination.page = 1
  await loadKnowledgeDocuments()
}

async function changeKnowledgeDocumentPage(page: number) {
  knowledgeDocumentPagination.page = page
  await loadKnowledgeDocuments()
}

function openKnowledgeRetrieve(row: any) {
  selectedKnowledgeBase.value = row
  knowledgeRetrieveForm.query = ''
  knowledgeRetrieveForm.top_k = 5
  knowledgeRetrieveForm.score_threshold = undefined
  knowledgeRetrieveResult.value = []
  knowledgeRetrieved.value = false
  knowledgeRetrieveVisible.value = true
}

async function runKnowledgeRetrieve() {
  if (!selectedKnowledgeBase.value) return
  if (!knowledgeRetrieveForm.query.trim()) { message.warning('请输入检索内容'); return }
  knowledgeRetrieving.value = true
  try {
    const { data } = await api.post(`/knowledge-bases/${selectedKnowledgeBase.value.id}/retrieve`, {
      query: knowledgeRetrieveForm.query.trim(),
      top_k: knowledgeRetrieveForm.top_k,
      score_threshold: knowledgeRetrieveForm.score_threshold ?? null
    })
    knowledgeRetrieveResult.value = data.hits || []
    knowledgeRetrieved.value = true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识库检索失败')
  } finally {
    knowledgeRetrieving.value = false
  }
}

function formatScore(value: any) {
  const numberValue = Number(value || 0)
  return Number.isFinite(numberValue) ? numberValue.toFixed(3) : '0.000'
}

function knowledgeWorkflowSerialNumber(index: number) {
  return (knowledgeWorkflowPagination.page - 1) * knowledgeWorkflowPagination.pageSize + index + 1
}

async function loadKnowledgeWorkflows() {
  const name = knowledgeWorkflowSearch.name.trim()
  const status = knowledgeWorkflowSearch.status
  const [listRes, allRes] = await Promise.all([
    api.get('/knowledge-workflows', {
      params: {
        ...(name ? { name } : {}),
        ...(status ? { status } : {}),
        page: knowledgeWorkflowPagination.page,
        page_size: knowledgeWorkflowPagination.pageSize
      }
    }),
    api.get('/knowledge-workflows')
  ])
  knowledgeWorkflowList.value = listRes.data.items
  knowledgeWorkflowPagination.total = listRes.data.total
  knowledgeWorkflowPagination.page = listRes.data.page
  knowledgeWorkflowPagination.pageSize = listRes.data.page_size
  knowledgeWorkflows.value = allRes.data
}

async function searchKnowledgeWorkflows() {
  knowledgeWorkflowPagination.page = 1
  await loadKnowledgeWorkflows()
}

async function resetKnowledgeWorkflowSearch() {
  knowledgeWorkflowSearch.name = ''
  knowledgeWorkflowSearch.status = ''
  knowledgeWorkflowPagination.page = 1
  await loadKnowledgeWorkflows()
}

async function changeKnowledgeWorkflowPage(page: number) {
  knowledgeWorkflowPagination.page = page
  await loadKnowledgeWorkflows()
}

function resetKnowledgeWorkflowForm() {
  knowledgeWorkflowForm.id = undefined
  knowledgeWorkflowForm.name = ''
  knowledgeWorkflowForm.api_base_url = ''
  knowledgeWorkflowForm.api_key_env = ''
  knowledgeWorkflowForm.status = 'active'
  knowledgeWorkflowForm.description = ''
}

function openCreateKnowledgeWorkflow() {
  resetKnowledgeWorkflowForm()
  knowledgeWorkflowFormVisible.value = true
}

function openEditKnowledgeWorkflow(row: any) {
  knowledgeWorkflowForm.id = row.id
  knowledgeWorkflowForm.name = row.name
  knowledgeWorkflowForm.api_base_url = row.api_base_url || ''
  knowledgeWorkflowForm.api_key_env = row.api_key_env || ''
  knowledgeWorkflowForm.status = row.status || 'active'
  knowledgeWorkflowForm.description = row.description || ''
  knowledgeWorkflowFormVisible.value = true
}

function validateKnowledgeWorkflowForm() {
  if (!knowledgeWorkflowForm.name.trim()) { message.warning('请输入工作流名称'); return false }
  if (!knowledgeWorkflowForm.api_key_env.trim()) { message.warning('请输入 API Key 环境变量名'); return false }
  return true
}

async function saveKnowledgeWorkflow() {
  if (!validateKnowledgeWorkflowForm()) return
  const payload = {
    name: knowledgeWorkflowForm.name.trim(),
    api_base_url: knowledgeWorkflowForm.api_base_url.trim(),
    api_key_env: knowledgeWorkflowForm.api_key_env.trim(),
    status: knowledgeWorkflowForm.status,
    description: knowledgeWorkflowForm.description.trim()
  }
  try {
    if (knowledgeWorkflowForm.id) {
      await api.put(`/knowledge-workflows/${knowledgeWorkflowForm.id}`, payload)
      message.success('工作流配置已更新')
    } else {
      await api.post('/knowledge-workflows', payload)
      knowledgeWorkflowPagination.page = 1
      message.success('工作流配置已创建')
    }
    knowledgeWorkflowFormVisible.value = false
    await loadKnowledgeWorkflows()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '工作流配置保存失败')
  }
}

async function checkKnowledgeWorkflow(row: any) {
  if (knowledgeWorkflowCheckingId.value !== null) {
    message.warning('上一次连接测试仍在进行中，请稍候')
    return
  }
  knowledgeWorkflowCheckingId.value = row.id
  try {
    await api.post(`/knowledge-workflows/${row.id}/check`)
    message.success('工作流连接测试成功')
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message
    message.error(detail ? `工作流连接测试失败：${detail}` : '工作流连接测试失败')
  } finally {
    knowledgeWorkflowCheckingId.value = null
  }
}

async function deleteKnowledgeWorkflow(row: any) {
  try {
    await confirmAction(`确认删除工作流配置「${row.name}」？`, '删除工作流配置', { confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await api.delete(`/knowledge-workflows/${row.id}`)
    if (knowledgeWorkflowList.value.length === 1 && knowledgeWorkflowPagination.page > 1) knowledgeWorkflowPagination.page -= 1
    await loadKnowledgeWorkflows()
    await loadQaSessions()
    message.success('工作流配置已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '工作流配置删除失败')
  }
}

async function loadQaSessions() {
  const { data } = await api.get('/knowledge-qa/sessions', {
    params: {
      ...(qaSessionSearch.project_id ? { project_id: qaSessionSearch.project_id } : {}),
      page: 1,
      page_size: 50
    }
  })
  qaSessions.value = data.items || []
  if (selectedQaSession.value && !qaSessions.value.some(item => item.id === selectedQaSession.value.id)) {
    selectedQaSession.value = null
    qaMessages.value = []
  }
}

async function searchQaSessions() {
  selectedQaSession.value = null
  qaMessages.value = []
  await loadQaSessions()
}

function resetQaSessionForm() {
  qaSessionForm.project_id = undefined
  qaSessionForm.workflow_id = undefined
  qaSessionForm.title = ''
}

function openCreateQaSession() {
  resetQaSessionForm()
  qaSessionFormVisible.value = true
}

function changeQaSessionProject() {
  qaSessionForm.workflow_id = undefined
  const first = qaSessionWorkflows.value[0]
  if (first) qaSessionForm.workflow_id = first.id
}

async function createQaSession() {
  if (!qaSessionForm.project_id) { message.warning('请选择项目'); return }
  if (!qaSessionForm.workflow_id) { message.warning('请选择工作流'); return }
  try {
    const { data } = await api.post('/knowledge-qa/sessions', {
      project_id: qaSessionForm.project_id,
      workflow_id: qaSessionForm.workflow_id,
      title: qaSessionForm.title.trim()
    })
    qaSessionFormVisible.value = false
    await loadQaSessions()
    await selectQaSession(data)
    message.success('会话已创建')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '会话创建失败')
  }
}

async function selectQaSession(session: any) {
  selectedQaSession.value = session
  qaQuestion.value = ''
  const { data } = await api.get(`/knowledge-qa/sessions/${session.id}/messages`)
  qaMessages.value = data || []
}

async function deleteQaSession(session: any) {
  try {
    await confirmAction(`确认删除会话「${session.title}」？`, '删除问答会话', { confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await api.delete(`/knowledge-qa/sessions/${session.id}`)
    selectedQaSession.value = null
    qaMessages.value = []
    await loadQaSessions()
    message.success('会话已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '会话删除失败')
  }
}

async function askKnowledgeQa() {
  if (!selectedQaSession.value) { message.warning('请先选择或新建会话'); return }
  const question = qaQuestion.value.trim()
  if (!question) { message.warning('请输入问题'); return }
  qaAsking.value = true
  try {
    const { data } = await api.post(`/knowledge-qa/sessions/${selectedQaSession.value.id}/ask`, { question })
    qaMessages.value.push(data.user_message, data.assistant_message)
    qaQuestion.value = ''
    await loadQaSessions()
    const latest = qaSessions.value.find(item => item.id === selectedQaSession.value.id)
    if (latest) selectedQaSession.value = latest
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '知识问答失败')
    if (selectedQaSession.value) {
      const { data } = await api.get(`/knowledge-qa/sessions/${selectedQaSession.value.id}/messages`)
      qaMessages.value = data || []
    }
  } finally {
    qaAsking.value = false
  }
}

const qaMessagesRef = ref<HTMLElement | null>(null)

async function scrollQaMessagesToBottom() {
  await nextTick()
  const el = qaMessagesRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  () => [qaMessages.value.length, selectedQaSession.value?.id] as const,
  () => { void scrollQaMessagesToBottom() }
)

function apiKeyConfigSerialNumber(index: number) {
  return (apiKeyConfigPagination.page - 1) * apiKeyConfigPagination.pageSize + index + 1
}

function normalizeEnvKey(value: string) {
  return value.trim().toUpperCase()
}

function validateEnvKey(value: string) {
  return /^[A-Z][A-Z0-9_]*$/.test(value)
}

async function loadApiKeyConfigs() {
  const { data } = await api.get('/api-key-configs', {
    params: {
      ...(apiKeyConfigSearch.keyword.trim() ? { keyword: apiKeyConfigSearch.keyword.trim() } : {}),
      ...(apiKeyConfigSearch.status ? { status: apiKeyConfigSearch.status } : {}),
      page: apiKeyConfigPagination.page,
      page_size: apiKeyConfigPagination.pageSize
    }
  })
  apiKeyConfigList.value = data.items
  apiKeyConfigs.value = data.items
  apiKeyConfigPagination.total = data.total
  apiKeyConfigPagination.page = data.page
  apiKeyConfigPagination.pageSize = data.page_size
}

async function loadWorkflowApiKeyOptions() {
  const { data } = await api.get('/api-key-configs/options')
  workflowApiKeyOptions.value = data || []
}

async function handleWorkflowApiKeyDropdown(visible: boolean) {
  if (visible) await loadWorkflowApiKeyOptions()
}

async function searchApiKeyConfigs() { apiKeyConfigPagination.page = 1; await loadApiKeyConfigs() }
async function resetApiKeyConfigSearch() { apiKeyConfigSearch.keyword = ''; apiKeyConfigSearch.status = ''; apiKeyConfigPagination.page = 1; await loadApiKeyConfigs() }
async function changeApiKeyConfigPage(page: number) { apiKeyConfigPagination.page = page; await loadApiKeyConfigs() }

function resetApiKeyConfigForm() {
  apiKeyConfigForm.id = undefined
  apiKeyConfigForm.env_key = ''
  apiKeyConfigForm.display_name = ''
  apiKeyConfigForm.status = 'active'
  apiKeyConfigForm.description = ''
}

function openCreateApiKeyConfig() { resetApiKeyConfigForm(); apiKeyConfigFormVisible.value = true }
function openEditApiKeyConfig(row: any) {
  apiKeyConfigForm.id = row.id
  apiKeyConfigForm.env_key = row.env_key || ''
  apiKeyConfigForm.display_name = row.display_name || ''
  apiKeyConfigForm.status = row.status || 'active'
  apiKeyConfigForm.description = row.description || ''
  apiKeyConfigFormVisible.value = true
}

async function saveApiKeyConfig() {
  const envKey = normalizeEnvKey(apiKeyConfigForm.env_key)
  const displayName = apiKeyConfigForm.display_name.trim()
  if (!displayName) { message.warning('请输入中文名'); return }
  if (!envKey) { message.warning('请输入环境变量名'); return }
  if (!validateEnvKey(envKey)) { message.warning('环境变量名只允许大写字母、数字、下划线，且必须以大写字母开头'); return }
  const payload = { env_key: envKey, display_name: displayName, status: apiKeyConfigForm.status, description: apiKeyConfigForm.description.trim() }
  try {
    if (apiKeyConfigForm.id) {
      await api.put(`/api-key-configs/${apiKeyConfigForm.id}`, payload)
      message.success('API Key配置已更新')
    } else {
      await api.post('/api-key-configs', payload)
      apiKeyConfigPagination.page = 1
      message.success('API Key配置已创建')
    }
    apiKeyConfigFormVisible.value = false
    await loadApiKeyConfigs()
    await loadWorkflowApiKeyOptions()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'API Key配置保存失败')
  }
}

async function deleteApiKeyConfig(row: any) {
  try {
    await confirmAction(`确认删除API Key配置「${row.display_name}」？`, '删除API Key配置', { confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await api.delete(`/api-key-configs/${row.id}`)
    if (apiKeyConfigList.value.length === 1 && apiKeyConfigPagination.page > 1) apiKeyConfigPagination.page -= 1
    await loadApiKeyConfigs()
    await loadWorkflowApiKeyOptions()
    message.success('API Key配置已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'API Key配置删除失败')
  }
}
function ticketCategoryText(category: string) {
  return ({ feature: '功能建议', issue: '问题反馈', experience: '体验优化', other: '其他' } as Record<string, string>)[category] || category
}

function ticketStatusText(status: string) {
  return ({ pending: '待处理', processing: '处理中', resolved: '已解决' } as Record<string, string>)[status] || status
}

function ticketStatusColor(status: string) {
  return status === 'resolved' ? 'success' : status === 'processing' ? 'processing' : 'warning'
}

async function loadTickets() {
  const { data } = await api.get('/tickets', { params: { ...(ticketSearch.title.trim() ? { title: ticketSearch.title.trim() } : {}), ...(ticketSearch.category ? { category: ticketSearch.category } : {}), ...(ticketSearch.status ? { status: ticketSearch.status } : {}), page: ticketPagination.page, page_size: ticketPagination.pageSize } })
  tickets.value = data.items
  ticketPagination.total = data.total
  ticketPagination.page = data.page
  ticketPagination.pageSize = data.page_size
}

async function searchTickets() { ticketPagination.page = 1; await loadTickets() }
async function resetTickets() { ticketSearch.title = ''; ticketSearch.category = ''; ticketSearch.status = ''; ticketPagination.page = 1; await loadTickets() }
async function changeTicketPage(page: number) { ticketPagination.page = page; await loadTickets() }
function resetTicketForm() { ticketForm.category = 'feature'; ticketForm.title = ''; ticketForm.content = ''; ticketForm.files = [] }
function openCreateTicket() { resetTicketForm(); createTicketVisible.value = true }
function validateTicketFile(file: any) { if (file.size > 20 * 1024 * 1024) { message.error('单个附件不能超过 20MB'); return false }; return false }

async function submitTicket() {
  if (!ticketForm.title.trim() || !ticketForm.content.trim()) { message.warning('请填写工单标题和建议内容'); return }
  ticketSubmitting.value = true
  try {
    const form = new FormData(); form.append('category', ticketForm.category); form.append('title', ticketForm.title.trim()); form.append('content', ticketForm.content.trim())
    ticketForm.files.forEach(item => form.append('files', item.originFileObj || item))
    await api.post('/tickets', form); createTicketVisible.value = false; ticketPagination.page = 1; await loadTickets(); message.success('工单已提交')
  } catch (error: any) { message.error(error?.response?.data?.detail || '工单提交失败') } finally { ticketSubmitting.value = false }
}

async function openTicketDetail(row: any) { try { ticketDetail.value = (await api.get(`/tickets/${row.id}`)).data; ticketDetailVisible.value = true } catch (error: any) { message.error(error?.response?.data?.detail || '工单详情加载失败') } }
function openProcessTicket() { if (!ticketDetail.value) return; ticketProcessForm.status = ticketDetail.value.status === 'resolved' ? 'resolved' : 'processing'; ticketProcessForm.reply = ticketDetail.value.reply || ''; processTicketVisible.value = true }
async function saveTicketProcess() {
  if (!ticketDetail.value) return
  if (ticketProcessForm.status === 'resolved' && !ticketProcessForm.reply.trim()) { message.warning('标记已解决时必须填写处理回复'); return }
  try { ticketDetail.value = (await api.put(`/tickets/${ticketDetail.value.id}/process`, { status: ticketProcessForm.status, reply: ticketProcessForm.reply.trim() })).data; processTicketVisible.value = false; await loadTickets(); message.success('工单已处理') } catch (error: any) { message.error(error?.response?.data?.detail || '工单处理失败') }
}
async function downloadTicketAttachment(ticket: any, item: any) {
  try { const response = await api.get(`/tickets/${ticket.id}/attachments/${item.id}`, { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const anchor = document.createElement('a'); anchor.href = url; anchor.download = item.name; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url) } catch (error: any) { message.error(error?.response?.data?.detail || '附件下载失败') }
}

function selectAiSourceFile(file: any) {
  const rawFile = file?.originFileObj || file
  if (!rawFile) return false
  if (rawFile.size > 20 * 1024 * 1024) {
    message.error('需求文档不能超过 20MB')
    return false
  }
  aiSourceFiles.value = [{ ...file, originFileObj: rawFile, status: 'done' }]
  aiLastUploadedFilename.value = rawFile.name || ''
  return false
}

function removeAiSourceFile() {
  aiSourceFiles.value = []
  aiLastUploadedFilename.value = ''
  return true
}

async function startAiGeneration() {
  const file = aiSourceFiles.value[0]?.originFileObj
  if (!file || aiGenerating.value) {
    return
  }
  aiGenerating.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    await api.post('/ai-case-generations', form)
    aiSourceFiles.value = []
    aiGenerationPagination.page = 1
    await loadAiGenerations()
    message.success('AI 生成任务已提交')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'AI 生成任务提交失败')
  } finally {
    aiGenerating.value = false
  }
}

async function downloadAiGenerationFile(row: any, index: number) {
  try {
    const file = row.output_files?.[index]
    const response = await api.get(`/ai-case-generations/${row.id}/files/${index}`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = file?.name || '测试用例.xlsx'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '生成文件下载失败')
  }
}

async function deleteAiGeneration(row: any) {
  try {
    await confirmAction('确认删除该生成历史及其保存的文件吗？删除后无法恢复。', '删除生成历史', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/ai-case-generations/${row.id}`)
    if (aiGenerations.value.length === 1 && aiGenerationPagination.page > 1) aiGenerationPagination.page -= 1
    await loadAiGenerations()
    message.success('生成历史已删除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '生成历史删除失败')
  }
}

function changeSelectedReports(keys: Array<string | number>) {
  selectedReportIds.value = keys.map(key => Number(key)).filter(Boolean)
}

function changeSelectedUiReports(keys: Array<string | number>) {
  selectedUiReportIds.value = keys.map(key => Number(key)).filter(Boolean)
}

async function loadLogs() {
  await Promise.allSettled([loadOperationLogs(), loadExecutionLogs(), loadExceptionLogs()])
}

async function loadOperationLogs() {
  const { data } = await api.get('/logs', {
    params: {
      ...(operationLogSearch.module.trim() ? { module: operationLogSearch.module.trim() } : {}),
      ...(operationLogSearch.action.trim() ? { action: operationLogSearch.action.trim() } : {}),
      ...(operationLogSearch.result ? { result: operationLogSearch.result } : {}),
      ...(operationLogSearch.start_time.trim() ? { start_time: operationLogSearch.start_time.trim() } : {}),
      ...(operationLogSearch.end_time.trim() ? { end_time: operationLogSearch.end_time.trim() } : {}),
      page: operationLogPagination.page,
      page_size: operationLogPagination.pageSize
    }
  })
  operationLogs.value = data.items
  logs.value = data.items
  operationLogPagination.total = data.total
  operationLogPagination.page = data.page
  operationLogPagination.pageSize = data.page_size
}

async function loadExecutionLogs() {
  const { data } = await api.get('/logs/executions', {
    params: {
      ...(executionLogSearch.name.trim() ? { name: executionLogSearch.name.trim() } : {}),
      ...(executionLogSearch.status ? { status: executionLogSearch.status } : {}),
      page: executionLogPagination.page,
      page_size: executionLogPagination.pageSize
    }
  })
  executionLogs.value = data.items
  executionLogPagination.total = data.total
  executionLogPagination.page = data.page
  executionLogPagination.pageSize = data.page_size
}

async function loadExceptionLogs() {
  const { data } = await api.get('/logs/exceptions', {
    params: {
      ...(exceptionLogSearch.name.trim() ? { name: exceptionLogSearch.name.trim() } : {}),
      ...(exceptionLogSearch.status ? { status: exceptionLogSearch.status } : {}),
      page: exceptionLogPagination.page,
      page_size: exceptionLogPagination.pageSize
    }
  })
  exceptionLogs.value = data.items
  exceptionLogPagination.total = data.total
  exceptionLogPagination.page = data.page
  exceptionLogPagination.pageSize = data.page_size
}

async function changeLogTab() {
  if (activeLogTab.value === 'operations') await loadOperationLogs()
  if (activeLogTab.value === 'executions') await loadExecutionLogs()
  if (activeLogTab.value === 'exceptions') await loadExceptionLogs()
}

async function searchOperationLogs() {
  operationLogPagination.page = 1
  await loadOperationLogs()
}

async function resetOperationLogSearch() {
  operationLogSearch.module = ''
  operationLogSearch.action = ''
  operationLogSearch.result = ''
  operationLogSearch.start_time = ''
  operationLogSearch.end_time = ''
  operationLogPagination.page = 1
  await loadOperationLogs()
}

async function changeOperationLogPage(page: number) {
  operationLogPagination.page = page
  await loadOperationLogs()
}

async function searchExecutionLogs() {
  executionLogPagination.page = 1
  await loadExecutionLogs()
}

async function resetExecutionLogSearch() {
  executionLogSearch.name = ''
  executionLogSearch.status = ''
  executionLogPagination.page = 1
  await loadExecutionLogs()
}

async function changeExecutionLogPage(page: number) {
  executionLogPagination.page = page
  await loadExecutionLogs()
}

async function searchExceptionLogs() {
  exceptionLogPagination.page = 1
  await loadExceptionLogs()
}

async function resetExceptionLogSearch() {
  exceptionLogSearch.name = ''
  exceptionLogSearch.status = ''
  exceptionLogPagination.page = 1
  await loadExceptionLogs()
}

async function changeExceptionLogPage(page: number) {
  exceptionLogPagination.page = page
  await loadExceptionLogs()
}

function openOperationLogDetail(row: any) {
  operationLogDetail.value = row
  operationLogDetailVisible.value = true
}

async function openExecutionLogDetail(row: any) {
  const { data } = await api.get(`/logs/executions/${row.id}`)
  executionLogDetail.value = data
  executionLogDetailVisible.value = true
}

function openExecutionLogReport(row: any) {
  window.open(`/api/executions/${row.task_id}/report`, '_blank')
}

const operationModuleMap: Record<string, string> = {
  auth: '认证',
  user: '用户管理',
  role: '角色管理',
  project: '项目管理',
  environment: '环境管理',
  api: '接口管理',
  case: '用例管理',
  plan: '测试计划',
  ticket: '工单管理',
  knowledge_project: '知识库项目',
  knowledge_base: '知识库',
  knowledge_workflow: '知识库工作流',
  api_key_config: 'API Key配置',
  knowledge_qa: '知识问答',
  log: '日志中心',
  system: '系统异常'
}

const operationActionMap: Record<string, string> = {
  login: '登录',
  logout: '退出登录',
  change_password: '修改密码',
  create: '创建',
  update: '编辑',
  delete: '删除',
  status: '修改状态',
  process: '处理',
  execute: '执行',
  generate_steps: '生成步骤',
  exception: '异常捕获'
}

const operationResultMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
  error: '异常'
}

function operationModuleText(value: string) {
  return operationModuleMap[value] || value || '-'
}

function operationActionText(value: string) {
  return operationActionMap[value] || value || '-'
}

function operationResultText(value: string) {
  return operationResultMap[value] || value || '-'
}

function operationContentText(value: string) {
  if (!value) return '-'
  const replacements: Array<[RegExp, string]> = [
    [/^user (.+) logged in$/, '用户 $1 登录'],
    [/^user (.+) logged out$/, '用户 $1 退出登录'],
    [/^user (.+) changed password$/, '用户 $1 修改密码'],
    [/^created user (.+)$/, '创建用户 $1'],
    [/^updated user (.+)$/, '编辑用户 $1'],
    [/^updated user (.+) status to active$/, '启用用户 $1'],
    [/^updated user (.+) status to disabled$/, '禁用用户 $1'],
    [/^created role (.+)$/, '创建角色 $1'],
    [/^updated role (.+)$/, '编辑角色 $1'],
    [/^deleted role (.+)$/, '删除角色 $1'],
    [/^created project (.+)$/, '创建项目 $1'],
    [/^updated project (.+)$/, '编辑项目 $1'],
    [/^deleted project (.+)$/, '删除项目 $1'],
    [/^created environment (.+)$/, '创建环境 $1'],
    [/^updated environment (.+)$/, '编辑环境 $1'],
    [/^deleted environment (.+)$/, '删除环境 $1'],
    [/^created api (.+)$/, '创建接口 $1'],
    [/^updated api (.+)$/, '编辑接口 $1'],
    [/^deleted api (.+)$/, '删除接口 $1'],
    [/^created case (.+)$/, '创建用例 $1'],
    [/^updated case (.+)$/, '编辑用例 $1'],
    [/^deleted case (.+)$/, '删除用例 $1'],
    [/^created plan (.+)$/, '创建测试计划 $1'],
    [/^updated plan (.+)$/, '编辑测试计划 $1'],
    [/^deleted plan (.+)$/, '删除测试计划 $1'],
    [/^executed plan (.+), task \d+$/, '执行测试计划 $1']
  ]
  for (const [pattern, label] of replacements) {
    if (pattern.test(value)) return value.replace(pattern, label)
  }
  return value
}

function logFailureSummary(row: any) {
  if (row.error_message) return row.error_message
  const assertion = row.failed_assertion || {}
  if (assertion.message) return assertion.message
  if (assertion.type) return `${assertion.type} ${assertion.path || ''} 期望 ${assertion.expected ?? '-'}，实际 ${assertion.actual ?? '-'}`
  return '-'
}

async function login() {
  if (loginLoading.value) {
    return
  }
  loginLoading.value = true
  try {
    const { data } = await api.post('/auth/login', loginForm)
    sessionExpired.value = false
    me.value = data.user
    openedTabs.value = [menuMeta.dashboard]
    active.value = 'dashboard'
    saveTabs()
    syncAllowedTabs()
    await loadAll()
  } catch (error: any) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      message.error(detail)
    } else if (status === 401) {
      message.error('用户名或密码错误')
    } else if (status === 422) {
      message.error('请输入用户名和密码')
    } else if (status === 502 || status === 503 || status === 504) {
      message.error(`服务暂时不可用（HTTP ${status}），请稍后重试`)
    } else if (status) {
      message.error(`登录失败（HTTP ${status}）`)
    } else if (error?.request) {
      message.error('无法连接到服务，请确认平台服务已启动')
    } else {
      message.error(error?.message || '登录请求发送失败')
    }
  } finally {
    loginLoading.value = false
  }
}

async function logout() {
  await api.post('/auth/logout')
  localStorage.removeItem('active_menu')
  localStorage.removeItem('opened_tabs')
  openedTabs.value = [menuMeta.dashboard]
  active.value = 'dashboard'
  me.value = null
}

function handleSessionExpired() {
  if (!me.value || sessionExpired.value) return
  sessionExpired.value = true
  localStorage.removeItem('active_menu')
  localStorage.removeItem('opened_tabs')
  openedTabs.value = [menuMeta.dashboard]
  active.value = 'dashboard'
  me.value = null
  message.warning('登录已过期，请重新登录')
}

function saveTabs() {
  localStorage.setItem('opened_tabs', JSON.stringify(openedTabs.value.map(tab => ({ name: tab.name }))))
  localStorage.setItem('active_menu', active.value)
}

function openTab(index: string) {
  if (!isMenuAllowed(index)) {
    message.warning('当前角色无权访问该功能')
    return
  }
  const tab = menuMeta[index]
  if (!tab) {
    return
  }
  if (!openedTabs.value.some(item => item.name === index)) {
    openedTabs.value.push(tab)
  }
  active.value = index
  saveTabs()
}

function openRuntimeTab(tab: AppTab) {
  if (!openedTabs.value.some(item => item.name === tab.name)) {
    openedTabs.value.push(tab)
  }
  active.value = tab.name
  saveTabs()
}

function selectMenu(index: string) {
  openTab(index)
}

function handleMenuSelect({ key }: { key: string }) {
  selectMenu(key)
  mobileSidebarOpen.value = false
}

function toggleSidebar() {
  if (isMobile.value) {
    mobileSidebarOpen.value = true
    return
  }
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function handleSidebarBreakpoint(broken: boolean) {
  isMobile.value = broken
  if (!broken) {
    mobileSidebarOpen.value = false
  }
}

function switchTab(name: string | number) {
  active.value = String(name)
  saveTabs()
}

async function closeTab(name: string | number) {
  const target = String(name)
  if (apiEditors[target]) {
    await requestCloseApiEditor(apiEditors[target])
    return
  }
  if (planEditors[target]) {
    await requestClosePlanEditor(planEditors[target])
    return
  }
  if (target === UI_CASE_CREATE_TAB || target.startsWith(UI_CASE_EDIT_PREFIX)) {
    closeUiCaseEditorTab(target)
    return
  }
  removeTab(target)
}

function handleTabEdit(targetKey: string | number, action: 'add' | 'remove') {
  if (action === 'remove') {
    void closeTab(targetKey)
  }
}

function removeTab(target: string) {
  const index = openedTabs.value.findIndex(tab => tab.name === target)
  const tab = openedTabs.value[index]
  if (index === -1 || !tab?.closable) {
    return
  }
  openedTabs.value.splice(index, 1)
  if (openedTabs.value.length === 0) {
    openedTabs.value = [menuMeta.dashboard]
  }
  if (active.value === target) {
    const next = openedTabs.value[index - 1] || openedTabs.value[index] || menuMeta.dashboard
    active.value = next.name
  }
  saveTabs()
}

async function handleUserCommand(command: string) {
  if (command === 'logout') {
    await logout()
  } else if (command === 'changePassword') {
    changePasswordDialogVisible.value = true
  }
}

function resetChangePasswordForm() {
  changePasswordForm.old_password = ''
  changePasswordForm.new_password = ''
  changePasswordForm.confirm_password = ''
}

function cancelChangePassword() {
  changePasswordDialogVisible.value = false
  resetChangePasswordForm()
}

function passwordsMismatch() {
  return Boolean(
    changePasswordForm.new_password &&
    changePasswordForm.confirm_password &&
    changePasswordForm.new_password !== changePasswordForm.confirm_password
  )
}

function validatePasswordMatch() {
  if (passwordsMismatch()) {
    message.warning('两次输入的新密码不一致')
    return false
  }
  return true
}

async function changePassword() {
  if (!changePasswordForm.old_password) {
    message.warning('请输入原密码')
    return
  }
  if (!changePasswordForm.new_password) {
    message.warning('请输入新密码')
    return
  }
  if (changePasswordForm.new_password.length < 6) {
    message.warning('新密码至少6位')
    return
  }
  if (!changePasswordForm.confirm_password) {
    message.warning('请再次输入新密码')
    return
  }
  if (passwordsMismatch()) {
    message.warning('两次输入的新密码不一致')
    return
  }
  if (changePasswordForm.old_password === changePasswordForm.new_password) {
    message.warning('新密码不能与原密码一致')
    return
  }
  try {
    await api.post('/auth/change-password', {
      old_password: changePasswordForm.old_password,
      new_password: changePasswordForm.new_password
    })
    changePasswordDialogVisible.value = false
    resetChangePasswordForm()
    message.success('密码修改成功')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '原密码错误')
  }
}

function resetUserForm() {
  userForm.username = ''
  userForm.real_name = ''
  userForm.role = roles.value.find(role => role.code === 'tester') ? 'tester' : roles.value[0]?.code || 'tester'
}

async function openCreateUserDialog() {
  if (!roles.value.length) await loadRoles()
  resetUserForm()
  createUserDialogVisible.value = true
}

function cancelCreateUser() {
  createUserDialogVisible.value = false
  resetUserForm()
}

function resetEditUserForm() {
  editUserForm.id = undefined
  editUserForm.username = ''
  editUserForm.real_name = ''
  editUserForm.role = roles.value.find(role => role.code === 'tester') ? 'tester' : roles.value[0]?.code || 'tester'
}

function openEditUserDialog(user: any) {
  editUserForm.id = user.id
  editUserForm.username = user.username
  editUserForm.real_name = user.real_name
  editUserForm.role = user.role || 'tester'
  editUserDialogVisible.value = true
}

function cancelEditUser() {
  editUserDialogVisible.value = false
  resetEditUserForm()
}

function statusText(status: string) {
  return status === 'active' ? '启用' : '禁用'
}

async function createUser() {
  const username = userForm.username.trim()
  const realName = userForm.real_name.trim()
  if (!username) {
    message.warning('请输入用户名')
    return
  }
  if (!realName) {
    message.warning('请输入姓名')
    return
  }
  if (!userForm.role) {
    message.warning('请选择角色')
    return
  }
  await api.post('/users', {
    username,
    password: '123456',
    real_name: realName,
    role: userForm.role
  })
  createUserDialogVisible.value = false
  resetUserForm()
  message.success('用户已创建')
  await loadUsers()
}

async function updateUser() {
  const username = editUserForm.username.trim()
  const realName = editUserForm.real_name.trim()
  if (!username) {
    message.warning('请输入用户名')
    return
  }
  if (!realName) {
    message.warning('请输入姓名')
    return
  }
  await api.put(`/users/${editUserForm.id}`, { username, real_name: realName, role: editUserForm.role })
  editUserDialogVisible.value = false
  resetEditUserForm()
  message.success('用户已更新')
  await loadUsers()
}

async function toggleUserStatus(user: any) {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  await api.patch(`/users/${user.id}/status`, { status: nextStatus })
  message.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
  await loadUsers()
}

function resetRoleForm() {
  roleForm.code = ''
  roleForm.name = ''
  roleForm.description = ''
  roleForm.status = 'active'
  roleForm.menus = ['dashboard']
}

function resetEditRoleForm() {
  editRoleForm.id = undefined
  editRoleForm.code = ''
  editRoleForm.name = ''
  editRoleForm.description = ''
  editRoleForm.status = 'active'
  editRoleForm.menus = []
  editRoleForm.is_builtin = false
}

function openCreateRoleDialog() {
  resetRoleForm()
  createRoleDialogVisible.value = true
}

function cancelCreateRole() {
  createRoleDialogVisible.value = false
  resetRoleForm()
}

function openEditRoleDialog(role: any) {
  editRoleForm.id = role.id
  editRoleForm.code = role.code
  editRoleForm.name = role.name
  editRoleForm.description = role.description || ''
  editRoleForm.status = role.status
  editRoleForm.menus = [...(role.menus || [])]
  editRoleForm.is_builtin = Boolean(role.is_builtin)
  editRoleDialogVisible.value = true
}

function cancelEditRole() {
  editRoleDialogVisible.value = false
  resetEditRoleForm()
}

function resetRolePermissionForm() {
  rolePermissionForm.id = undefined
  rolePermissionForm.name = ''
  rolePermissionForm.description = ''
  rolePermissionForm.status = 'active'
  rolePermissionForm.menus = []
}

function openRolePermissionDialog(role: any) {
  rolePermissionForm.id = role.id
  rolePermissionForm.name = role.name
  rolePermissionForm.description = role.description || ''
  rolePermissionForm.status = role.status
  rolePermissionForm.menus = [...(role.menus || [])]
  rolePermissionDialogVisible.value = true
}

function cancelRolePermission() {
  rolePermissionDialogVisible.value = false
  resetRolePermissionForm()
}

async function saveRolePermissions() {
  if (!rolePermissionForm.id) return
  const menus = rolePermissionForm.menus.filter(key => roleMenuLeafKeys.value.has(key))
  await api.put(`/roles/${rolePermissionForm.id}`, {
    name: rolePermissionForm.name,
    description: rolePermissionForm.description,
    status: rolePermissionForm.status,
    menus
  })
  rolePermissionDialogVisible.value = false
  message.success('菜单权限已更新')
  await loadRoles()
  const { data } = await api.get('/auth/me')
  me.value = data
  syncAllowedTabs()
}

function roleMenuLabels(menus: string[]) {
  const labels = new Map<string, string>()
  roleMenus.value.forEach(group => {
    if (group.children?.length) group.children.forEach((child: any) => labels.set(child.key, child.label))
    else labels.set(group.key, group.label)
  })
  return (menus || []).map(key => labels.get(key)).filter(Boolean)
}

async function createRole() {
  if (!roleForm.code.trim()) {
    message.warning('请输入角色编码')
    return
  }
  if (!roleForm.name.trim()) {
    message.warning('请输入角色名称')
    return
  }
  await api.post('/roles', {
    code: roleForm.code.trim(),
    name: roleForm.name.trim(),
    description: roleForm.description.trim(),
    status: roleForm.status,
    menus: roleForm.menus
  })
  createRoleDialogVisible.value = false
  resetRoleForm()
  message.success('角色已创建')
  await loadRoles()
}

async function updateRole() {
  if (!editRoleForm.name.trim()) {
    message.warning('请输入角色名称')
    return
  }
  await api.put(`/roles/${editRoleForm.id}`, {
    name: editRoleForm.name.trim(),
    description: editRoleForm.description.trim(),
    status: editRoleForm.status,
    menus: editRoleForm.menus
  })
  editRoleDialogVisible.value = false
  resetEditRoleForm()
  message.success('角色已更新')
  await loadRoles()
  const { data } = await api.get('/auth/me')
  me.value = data
  syncAllowedTabs()
}

async function deleteRole(role: any) {
  await confirmAction(`确认删除角色 ${role.name}？`, '删除角色', { confirmButtonText: '删除' })
  await api.delete(`/roles/${role.id}`)
  message.success('角色已删除')
  await loadRoles()
}

function resetProjectForm() {
  projectForm.name = ''
  projectForm.description = ''
}

function openCreateProjectDialog() {
  createProjectDialogVisible.value = true
}

function cancelCreateProject() {
  createProjectDialogVisible.value = false
  resetProjectForm()
}

function resetEditProjectForm() {
  editProjectForm.id = undefined
  editProjectForm.name = ''
  editProjectForm.description = ''
}

function openEditProjectDialog(project: any) {
  editProjectForm.id = project.id
  editProjectForm.name = project.name
  editProjectForm.description = project.description || ''
  editProjectDialogVisible.value = true
}

function cancelEditProject() {
  editProjectDialogVisible.value = false
  resetEditProjectForm()
}

async function refreshProjectsAfterChange() {
  await Promise.all([
    api.get('/projects').then(r => projects.value = r.data),
    loadProjects()
  ])
}

async function refreshProjectsAfterDelete() {
  await refreshProjectsAfterChange()
  if (projectList.value.length === 0 && projectPagination.page > 1) {
    projectPagination.page -= 1
    await loadProjects()
  }
}

async function createProject() {
  const name = projectForm.name.trim()
  const description = projectForm.description.trim()
  if (!name) {
    message.warning('请输入项目名称')
    return
  }
  if (!description) {
    message.warning('请输入描述')
    return
  }
  if (projects.value.some(project => project.name === name)) {
    message.warning('项目名称已存在')
    return
  }
  try {
    await api.post('/projects', { name, description })
    createProjectDialogVisible.value = false
    resetProjectForm()
    message.success('项目已创建')
    await refreshProjectsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '项目创建失败')
  }
}

async function updateProject() {
  const name = editProjectForm.name.trim()
  if (!name) {
    message.warning('请输入项目名称')
    return
  }
  await api.put(`/projects/${editProjectForm.id}`, { name, description: editProjectForm.description })
  editProjectDialogVisible.value = false
  resetEditProjectForm()
  message.success('项目已更新')
  await refreshProjectsAfterChange()
}

async function deleteProject(project: any) {
  try {
    await confirmAction('确认删除该项目吗？', '删除项目', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/projects/${project.id}`)
  message.success('项目已删除')
  await refreshProjectsAfterDelete()
}

function resetEnvironmentForm() {
  envForm.project_id = undefined
  envForm.name = ''
  envForm.protocol = ''
  envForm.base_url = ''
  envForm.port = ''
}

function openCreateEnvironmentDialog() {
  createEnvironmentDialogVisible.value = true
}

function cancelCreateEnvironment() {
  createEnvironmentDialogVisible.value = false
  resetEnvironmentForm()
}

function resetEditEnvironmentForm() {
  editEnvironmentForm.id = undefined
  editEnvironmentForm.project_id = undefined
  editEnvironmentForm.name = ''
  editEnvironmentForm.protocol = ''
  editEnvironmentForm.base_url = ''
  editEnvironmentForm.port = ''
}

function openEditEnvironmentDialog(environment: any) {
  editEnvironmentForm.id = environment.id
  editEnvironmentForm.project_id = environment.project_id
  editEnvironmentForm.name = environment.name
  editEnvironmentForm.protocol = environment.protocol || ''
  editEnvironmentForm.base_url = environment.base_url
  editEnvironmentForm.port = environment.port ? String(environment.port) : ''
  editEnvironmentDialogVisible.value = true
}

function cancelEditEnvironment() {
  editEnvironmentDialogVisible.value = false
  resetEditEnvironmentForm()
}

async function refreshEnvironmentsAfterChange() {
  await Promise.all([
    api.get('/environments').then(r => environments.value = r.data),
    loadEnvironments()
  ])
}

async function refreshEnvironmentsAfterDelete() {
  await refreshEnvironmentsAfterChange()
  if (environmentList.value.length === 0 && environmentPagination.page > 1) {
    environmentPagination.page -= 1
    await loadEnvironments()
  }
}

function environmentNameExists(projectId: number, name: string, environmentId?: number) {
  return environments.value.some(environment =>
    environment.project_id === projectId &&
    environment.name === name &&
    environment.id !== environmentId
  )
}

function digitsOnly(value: string) {
  return String(value || '').replace(/\D/g, '')
}

function validateEnvironmentProtocol(protocol: string) {
  if (!protocol) {
    message.warning('请选择协议')
    return false
  }
  return true
}

function environmentPort(protocol: string, port: string) {
  if (port) {
    return Number(port)
  }
  return protocol === 'http' ? 80 : 443
}

async function createEnvironment() {
  const projectId = envForm.project_id
  const name = envForm.name.trim()
  const protocol = envForm.protocol
  const baseUrl = envForm.base_url.trim()
  const port = environmentPort(protocol, envForm.port)
  if (!projectId) {
    message.warning('请选择项目')
    return
  }
  if (!name) {
    message.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    message.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    message.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name)) {
    message.warning('环境名称已存在')
    return
  }
  try {
    await api.post('/environments', { project_id: projectId, name, protocol, base_url: baseUrl, port, headers: {}, variables: {} })
    createEnvironmentDialogVisible.value = false
    resetEnvironmentForm()
    message.success('环境已创建')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '环境创建失败')
  }
}

async function updateEnvironment() {
  const projectId = editEnvironmentForm.project_id
  const name = editEnvironmentForm.name.trim()
  const protocol = editEnvironmentForm.protocol
  const baseUrl = editEnvironmentForm.base_url.trim()
  const port = environmentPort(protocol, editEnvironmentForm.port)
  if (!projectId) {
    message.warning('请选择项目')
    return
  }
  if (!name) {
    message.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    message.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    message.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name, editEnvironmentForm.id)) {
    message.warning('环境名称已存在')
    return
  }
  try {
    await api.put(`/environments/${editEnvironmentForm.id}`, { project_id: projectId, name, protocol, base_url: baseUrl, port })
    editEnvironmentDialogVisible.value = false
    resetEditEnvironmentForm()
    message.success('环境已更新')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '环境更新失败')
  }
}

async function deleteEnvironment(environment: any) {
  try {
    await confirmAction('确认删除该环境吗？', '删除环境', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/environments/${environment.id}`)
  message.success('环境已删除')
  await refreshEnvironmentsAfterDelete()
}

function mockContentType(format: MockBodyFormat = 'json') {
  if (format === 'xml') return 'application/xml'
  if (format === 'text') return 'text/plain; charset=utf-8'
  return 'application/json'
}

function defaultMockHeaders(format: MockBodyFormat = 'json') {
  return [nextApiRow('Content-Type', mockContentType(format))]
}

function backendOrigin() {
  const origin = window.location.origin
  try {
    const url = new URL(origin)
    if (url.port === '5173') {
      url.port = '8000'
      return url.origin
    }
  } catch {}
  return origin
}

function mockAbsoluteUrl(row: { environment_id?: number; path?: string }) {
  if (!row.environment_id || !String(row.path || '').trim()) return ''
  return joinUrl(`${backendOrigin()}/mock-api/env/${row.environment_id}`, String(row.path || ''))
}

function syncMockContentType(form: MockFormState) {
  const value = mockContentType(form.body_format)
  const row = form.headerRows.find(item => item.key.trim().toLowerCase() === 'content-type')
  if (row) {
    row.value = value
  } else {
    form.headerRows.push(nextApiRow('Content-Type', value))
  }
}

function changeMockBodyFormat(form: MockFormState) {
  syncMockContentType(form)
}

function resetMockForm() {
  mockForm.id = undefined
  mockForm.project_id = undefined
  mockForm.environment_id = undefined
  mockForm.name = ''
  mockForm.method = 'GET'
  mockForm.path = ''
  mockForm.status = 'active'
  mockForm.status_code = '200'
  mockForm.delay_ms = '0'
  mockForm.headerRows = defaultMockHeaders()
  mockForm.response_body = '{\n  "code": 0,\n  "message": "success"\n}'
  mockForm.body_format = 'json'
  mockForm.sm3_enabled = false
  mockForm.description = ''
}

function resetEditMockForm() {
  editMockForm.id = undefined
  editMockForm.project_id = undefined
  editMockForm.environment_id = undefined
  editMockForm.name = ''
  editMockForm.method = 'GET'
  editMockForm.path = ''
  editMockForm.status = 'active'
  editMockForm.status_code = '200'
  editMockForm.delay_ms = '0'
  editMockForm.headerRows = []
  editMockForm.response_body = ''
  editMockForm.body_format = 'json'
  editMockForm.sm3_enabled = false
  editMockForm.description = ''
}

function openCreateMockDialog() {
  resetMockForm()
  createMockDialogVisible.value = true
}

function openEditMockDialog(row: any) {
  editMockForm.id = row.id
  editMockForm.project_id = row.project_id
  editMockForm.environment_id = row.environment_id
  editMockForm.name = row.name || ''
  editMockForm.method = row.method || 'GET'
  editMockForm.path = row.path || ''
  editMockForm.status = row.status || 'active'
  editMockForm.status_code = String(row.status_code || 200)
  editMockForm.delay_ms = String(row.delay_ms || 0)
  editMockForm.headerRows = objectToRows(row.headers, defaultMockHeaders(row.body_format || 'json'))
  editMockForm.response_body = row.response_body || ''
  editMockForm.body_format = ['json', 'xml', 'text'].includes(row.body_format) ? row.body_format : 'json'
  editMockForm.sm3_enabled = !!row.sm3_enabled
  editMockForm.description = row.description || ''
  editMockDialogVisible.value = true
}

function cancelCreateMock() {
  createMockDialogVisible.value = false
  resetMockForm()
}

function cancelEditMock() {
  editMockDialogVisible.value = false
  resetEditMockForm()
}

function changeMockFormProject() {
  mockForm.environment_id = undefined
}

  function changeEditMockFormProject() {
    editMockForm.environment_id = undefined
  }

  function defaultUiStep(action = 'goto'): UiStepRow {
    return {
      id: Date.now() + Math.floor(Math.random() * 1000),
      action,
      locator_type: action === 'goto' || action === 'wait' || action === 'screenshot' ? 'css' : 'css',
      target: '',
      value: action === 'wait' ? '1000' : '',
      description: ''
    }
  }

  function resetUiCaseForm() {
    uiCaseForm.id = undefined
    uiCaseForm.project_id = undefined
    uiCaseForm.environment_id = undefined
    uiCaseForm.name = ''
    uiCaseForm.start_url = '/'
    uiCaseForm.description = ''
    uiCaseForm.execution_mode = 'ai'
    uiCaseForm.test_goal = ''
    uiCaseForm.test_data_text = '{}'
    uiCaseForm.assertion_goal = ''
    uiCaseForm.max_steps = 30
    uiCaseForm.step_timeout_ms = 10000
    uiCaseForm.allow_ai_actions = true
    uiCaseForm.status = 'active'
    uiCaseForm.browser_channel = 'chromium'
    uiCaseForm.headless = true
    uiCaseForm.wait_until = 'networkidle'
    uiCaseForm.wait_after_load_ms = 500
    uiCaseForm.steps = []
  }

  function resetEditUiCaseForm() {
    editUiCaseForm.id = undefined
    editUiCaseForm.project_id = undefined
    editUiCaseForm.environment_id = undefined
    editUiCaseForm.name = ''
    editUiCaseForm.start_url = '/'
    editUiCaseForm.description = ''
    editUiCaseForm.execution_mode = 'ai'
    editUiCaseForm.test_goal = ''
    editUiCaseForm.test_data_text = '{}'
    editUiCaseForm.assertion_goal = ''
    editUiCaseForm.max_steps = 30
    editUiCaseForm.step_timeout_ms = 10000
    editUiCaseForm.allow_ai_actions = true
    editUiCaseForm.status = 'active'
    editUiCaseForm.browser_channel = 'chromium'
    editUiCaseForm.headless = true
    editUiCaseForm.wait_until = 'networkidle'
    editUiCaseForm.wait_after_load_ms = 500
    editUiCaseForm.steps = []
  }

  function openCreateUiCaseDialog() {
    resetUiCaseForm()
    closeExistingUiCaseEditorTabs()
    openRuntimeTab({ name: UI_CASE_CREATE_TAB, label: '新增UI用例', closable: true })
  }

  function openEditUiCaseDialog(row: any) {
    closeExistingUiCaseEditorTabs()
    editUiCaseForm.id = row.id
    editUiCaseForm.project_id = row.project_id
    editUiCaseForm.environment_id = row.environment_id
    editUiCaseForm.name = row.name || ''
    editUiCaseForm.start_url = row.start_url || '/'
    editUiCaseForm.description = row.description || ''
    editUiCaseForm.execution_mode = row.execution_mode === 'ai' ? 'ai' : 'advanced'
    editUiCaseForm.test_goal = row.test_goal || ''
    editUiCaseForm.test_data_text = JSON.stringify(row.test_data || {}, null, 2)
    editUiCaseForm.assertion_goal = row.assertion_goal || ''
    editUiCaseForm.max_steps = Number(row.max_steps ?? 30)
    editUiCaseForm.step_timeout_ms = Number(row.step_timeout_ms ?? 10000)
    editUiCaseForm.allow_ai_actions = row.allow_ai_actions !== false
    editUiCaseForm.status = row.status || 'active'
    editUiCaseForm.browser_channel = row.browser_channel || 'chromium'
    editUiCaseForm.headless = row.headless !== false
    editUiCaseForm.wait_until = row.wait_until || 'networkidle'
    editUiCaseForm.wait_after_load_ms = Number(row.wait_after_load_ms ?? 500)
    editUiCaseForm.steps = (row.steps || []).map((step: any) => ({ id: Date.now() + Math.floor(Math.random() * 1000), ...step }))
    syncUiStepIds(editUiCaseForm)
    openRuntimeTab({ name: `${UI_CASE_EDIT_PREFIX}${row.id}`, label: `编辑UI用例：${row.name || row.id}`, closable: true })
  }

  function changeUiCaseFormProject() {
    uiCaseForm.environment_id = undefined
  }

  function changeEditUiCaseFormProject() {
    editUiCaseForm.environment_id = undefined
  }

  function changeUiCaseEditorProject(form: UiCaseFormState) {
    form.environment_id = undefined
  }

  function uiCaseEditorEnvironments(form: UiCaseFormState) {
    return environments.value.filter(item => form.project_id && item.project_id === form.project_id)
  }

  function closeExistingUiCaseEditorTabs() {
    openedTabs.value
      .filter(tab => tab.name === UI_CASE_CREATE_TAB || tab.name.startsWith(UI_CASE_EDIT_PREFIX))
      .forEach(tab => removeTab(tab.name))
    resetUiCaseForm()
    resetEditUiCaseForm()
  }

  function closeUiCaseEditorTab(tabName: string) {
    removeTab(tabName)
    if (tabName === UI_CASE_CREATE_TAB) {
      resetUiCaseForm()
    } else {
      resetEditUiCaseForm()
    }
  }

  function closeUiCaseEditorFromPage() {
    const editor = activeUiCaseEditor.value
    if (!editor) return
    closeUiCaseEditorTab(editor.tabName)
  }

  async function saveUiCaseEditor() {
    const editor = activeUiCaseEditor.value
    if (!editor) return
    if (editor.mode === 'create') {
      await createUiCase()
    } else {
      await updateUiCase()
    }
  }

  function addUiStep(form: UiCaseFormState) {
    form.steps.push(defaultUiStep('click'))
    syncUiStepIds(form)
  }

  function openAiStepDialog(form: UiCaseFormState) {
    aiStepGenerator.targetForm = form
    aiStepGenerator.prompt = form.description || ''
    aiStepGenerator.mode = 'append'
    aiStepGenerator.generatedSteps = []
    aiStepDialogVisible.value = true
  }

  function resetAiStepGenerator() {
    aiStepDialogVisible.value = false
    aiStepGenerator.targetForm = null
    aiStepGenerator.prompt = ''
    aiStepGenerator.mode = 'append'
    aiStepGenerator.generatedSteps = []
    aiStepGenerator.loading = false
  }

  function normalizeGeneratedUiStep(step: any): UiStepRow {
    return {
      id: Date.now() + Math.floor(Math.random() * 100000),
      action: step?.action || 'click',
      locator_type: step?.locator_type || 'ai',
      target: step?.target || '',
      value: step?.value || '',
      description: step?.description || ''
    }
  }

  async function generateUiStepsFromPrompt() {
    const form = aiStepGenerator.targetForm
    const prompt = aiStepGenerator.prompt.trim()
    if (!form) return
    if (!prompt) {
      message.warning('请输入执行描述')
      return
    }
    aiStepGenerator.loading = true
    try {
      const { data } = await api.post('/ui-cases/generate-steps', {
        prompt,
        start_url: form.start_url,
        existing_steps: form.steps.map(({ action, locator_type, target, value, description }) => ({ action, locator_type, target, value, description }))
      })
      aiStepGenerator.generatedSteps = (data.steps || []).map(normalizeGeneratedUiStep)
      if (!aiStepGenerator.generatedSteps.length) {
        message.warning('未生成可用步骤')
      } else {
        message.success('步骤已生成，可预览后应用')
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '生成步骤失败')
    } finally {
      aiStepGenerator.loading = false
    }
  }

  function applyGeneratedUiSteps() {
    const form = aiStepGenerator.targetForm
    if (!form || !aiStepGenerator.generatedSteps.length) return
    const steps = aiStepGenerator.generatedSteps.map(step => ({ ...step, id: Date.now() + Math.floor(Math.random() * 100000) }))
    if (aiStepGenerator.mode === 'replace') {
      form.steps = steps
    } else {
      form.steps.push(...steps)
    }
    syncUiStepIds(form)
    message.success('已应用生成步骤')
    resetAiStepGenerator()
  }

  function removeUiStep(form: UiCaseFormState, index: number) {
    form.steps.splice(index, 1)
    syncUiStepIds(form)
  }

  function moveUiStep(form: UiCaseFormState, index: number, offset: number) {
    const target = index + offset
    if (target < 0 || target >= form.steps.length) return
    const [row] = form.steps.splice(index, 1)
    form.steps.splice(target, 0, row)
    syncUiStepIds(form)
  }

  function syncUiStepIds(form: UiCaseFormState) {
    form.steps.forEach((step, index) => {
      step.id = index + 1
    })
  }

  function uiStepRowProps(form: UiCaseFormState, index: number) {
    return {
      class: uiStepDrag.form === form && uiStepDrag.index === index ? 'ui-step-row-dragging' : '',
      onDragover: (event: DragEvent) => {
        if (uiStepDrag.form !== form) return
        event.preventDefault()
        if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
      },
      onDrop: (event: DragEvent) => dropUiStepRow(form, index, event),
      onDragend: resetUiStepDrag
    }
  }

  function activeUiStepRowProps(_record: UiStepRow, index: number) {
    const editor = activeUiCaseEditor.value
    return editor ? uiStepRowProps(editor.form, index) : {}
  }

  function isInteractiveUiStepTarget(target: EventTarget | null) {
    const element = target instanceof HTMLElement ? target : null
    if (!element) return false
    return Boolean(element.closest('input, textarea, select, button, [contenteditable="true"], .ant-input, .ant-select, .ant-input-number, .ant-picker'))
  }

  function startUiStepDrag(form: UiCaseFormState, index: number, event: DragEvent) {
    if (isInteractiveUiStepTarget(event.target)) {
      event.preventDefault()
      resetUiStepDrag()
      return
    }
    uiStepDrag.form = form
    uiStepDrag.index = index
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(index))
    }
  }

  function dropUiStepRow(form: UiCaseFormState, index: number, event: DragEvent) {
    event.preventDefault()
    const from = uiStepDrag.form === form ? uiStepDrag.index : Number(event.dataTransfer?.getData('text/plain') ?? -1)
    resetUiStepDrag()
    if (from < 0 || from === index || from >= form.steps.length) return
    const [row] = form.steps.splice(from, 1)
    form.steps.splice(index, 0, row)
    syncUiStepIds(form)
  }

  function resetUiStepDrag() {
    uiStepDrag.form = null
    uiStepDrag.index = -1
  }

  function resetUiPickerState() {
    if (uiPicker.screenshotUrl) {
      URL.revokeObjectURL(uiPicker.screenshotUrl)
    }
    uiPicker.sessionId = ''
    uiPicker.status = ''
    uiPicker.statusText = '未启动'
    uiPicker.message = ''
    uiPicker.xpath = ''
    uiPicker.summaryText = ''
    uiPicker.lastPickKey = ''
    uiPicker.pendingResult = null
    uiPicker.targetRow = null
    uiPicker.targetForm = null
    uiPicker.mode = 'operate'
    uiPicker.recordAction = 'click'
    uiPicker.recordActionAuto = true
    uiPicker.inputText = ''
    uiPicker.screenshotUrl = ''
    uiPicker.viewportWidth = 1366
    uiPicker.viewportHeight = 1050
    uiPicker.zoomPercent = 100
    uiPicker.loading = false
  }

  function uiPickerStatusText(status: string) {
    const mapping: Record<string, string> = {
      starting: '启动中',
      ready: '待拾取',
      picked: '已拾取',
      closed: '已关闭',
      error: '异常'
    }
    return mapping[status] || status || '未知'
  }

  function uiPickedSummary(result: any) {
    const summary = result?.summary || {}
    const parts = [
      summary.tag ? `标签：${summary.tag}` : '',
      summary.id ? `ID：${summary.id}` : '',
      summary.name ? `Name：${summary.name}` : '',
      summary.text ? `文本：${summary.text}` : ''
    ].filter(Boolean)
    return parts.join('，')
  }

  function stopUiPickerPolling() {
    if (uiPickerTimer) {
      window.clearInterval(uiPickerTimer)
      uiPickerTimer = undefined
    }
  }

  function friendlyUiPickerMessage(errorText: string, fallback = '启动拾取会话失败') {
    const text = String(errorText || '')
    if (/crashpad|no display|x server|headless=false|Target page|browser has been closed/i.test(text)) {
      return '远程浏览器启动失败，请检查服务器浏览器依赖和容器运行环境。'
    }
    return text || fallback
  }

  function sanitizeUiOptionText(value: any) {
    const text = String(value ?? '').replace(/\s+/g, ' ').trim()
    if (!text || /^(undefined|null|NaN)$/i.test(text) || /\bundefined\b|\bnull\b/i.test(text)) return ''
    return text
  }

  function isValidUiOptionText(value: any) {
    return !!sanitizeUiOptionText(value)
  }

  function uiPickerOptionLabel(option: any) {
    const label = sanitizeUiOptionText(option?.label)
    const originalValue = sanitizeUiOptionText(option?.originalValue)
    const value = sanitizeUiOptionText(option?.value)
    const text = label || value || originalValue || '未命名选项'
    if (originalValue && label && originalValue !== label) {
      return `${label}（${originalValue}）`
    }
    return text
  }

  function selectedUiPickerOptionValue() {
    const selectedOption = uiPickerSelectOptions.value.find((option: any) => option.selected)
    const currentValue = sanitizeUiOptionText(uiPicker.pendingResult?.summary?.value)
    return selectedOption?.value || currentValue || ''
  }

  function inferUiRecordAction(result = uiPicker.pendingResult): UiRecordAction {
    const summary = result?.summary || {}
    const tag = String(summary.tag || '').toLowerCase()
    const type = String(summary.type || '').toLowerCase()
    const hasInputValue = !!uiPicker.inputText.trim()
    const hasOptions = Array.isArray(summary.options) && summary.options.some((option: any) => isValidUiOptionText(option?.value) || isValidUiOptionText(option?.label))
    if ((tag === 'select' || hasOptions) && hasInputValue) return 'select'
    if ((tag === 'input' || tag === 'textarea') && !['button', 'submit', 'reset', 'checkbox', 'radio'].includes(type) && hasInputValue) return 'fill'
    return 'click'
  }

  function refreshAutoUiRecordAction() {
    if (!uiPicker.recordActionAuto || uiPicker.targetRow) return
    uiPicker.recordAction = inferUiRecordAction()
  }

  function disableUiRecordActionAuto() {
    uiPicker.recordActionAuto = false
  }

  function handleUiPickerSelectChange() {
    uiPicker.recordAction = 'select'
    uiPicker.recordActionAuto = true
  }

  function changeUiPickerZoom(delta: number) {
    uiPicker.zoomPercent = Math.min(200, Math.max(50, uiPicker.zoomPercent + delta))
  }

  function resetUiPickerZoom() {
    uiPicker.zoomPercent = 100
  }

  function handleUiPickerZoomWheel(event: WheelEvent) {
    changeUiPickerZoom(event.deltaY > 0 ? -10 : 10)
  }

  function uiStepDescription(action: string, result?: any) {
    const summary = result?.summary || {}
    const text = String(summary.text || '').trim()
    const tag = String(summary.tag || '').trim()
    const name = text || summary.name || summary.id || tag || '目标元素'
    const mapping: Record<string, string> = {
      click: `点击 ${name}`,
      dblclick: `双击 ${name}`,
      fill: `输入 ${name}`,
      select: `选择 ${name}`,
      assert_visible: `断言 ${name} 可见`,
      assert_text: `断言 ${name} 文本`,
      wait: '等待',
      screenshot: '截图'
    }
    return mapping[action] || ''
  }

  function uiActionText(action: string) {
    const mapping: Record<string, string> = {
      goto: '打开页面',
      click: '点击',
      dblclick: '双击',
      fill: '输入',
      select: '选择',
      wait: '等待',
      assert_text: '断言文本',
      assert_visible: '断言元素',
      screenshot: '截图'
    }
    return mapping[action] || action || '-'
  }

  function uiLocatorText(locatorType: string) {
    const mapping: Record<string, string> = {
      css: 'CSS',
      xpath: 'XPath',
      text: '文本',
      placeholder: '占位符',
      role: '按钮文字',
      ai: 'AI描述'
    }
    return mapping[locatorType] || locatorType || '-'
  }

  function buildRecordedUiStep(result: any) {
    if (!uiPicker.targetForm) return
    const action = uiPicker.recordActionAuto ? inferUiRecordAction(result) : uiPicker.recordAction
    const xpath = result?.xpath || ''
    if (!xpath) return
    const step = defaultUiStep(action)
    step.locator_type = 'xpath'
    step.target = xpath
    step.value = action === 'fill' || action === 'select' || action === 'assert_text' ? uiPicker.inputText.trim() : ''
    step.description = uiStepDescription(action, result)
    return step
  }

  function currentUiPickerSelectOption() {
    return uiPickerSelectOptions.value.find((option: any) => option.value === uiPicker.inputText.trim())
  }

  function markUiPickerSelectedOption(value: string) {
    const summary = uiPicker.pendingResult?.summary
    if (!summary || !Array.isArray(summary.options)) return
    summary.value = value
    summary.options = summary.options.map((option: any) => {
      const optionValue = sanitizeUiOptionText(option?.value ?? option?.label ?? option?.text ?? option?.name)
      const optionLabel = sanitizeUiOptionText(option?.label ?? option?.text ?? option?.name ?? option?.value)
      return { ...option, selected: optionValue === value || optionLabel === value }
    })
  }

  async function applyUiPickerSelect(showSuccess = true) {
    if (!uiPicker.sessionId || !uiPicker.pendingResult?.xpath || !uiPicker.inputText.trim()) return false
    const option = currentUiPickerSelectOption()
    try {
      const { data } = await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/select`, {
        xpath: uiPicker.pendingResult.xpath,
        value: uiPicker.inputText.trim(),
        label: option?.label || ''
      })
      uiPicker.status = data.status || uiPicker.status
      uiPicker.statusText = uiPickerStatusText(uiPicker.status)
      uiPicker.message = friendlyUiPickerMessage(data.error, data.message || '远程页面已完成选择')
      markUiPickerSelectedOption(uiPicker.inputText.trim())
      await refreshUiPickerScreenshot()
      if (showSuccess) message.success('远程页面已选择该选项')
      return true
    } catch (error: any) {
      uiPicker.message = error?.response?.data?.detail || '远程页面选择失败'
      return false
    }
  }

  async function confirmAppendRecordedUiStep() {
    if (!uiPicker.targetForm || !uiPicker.pendingResult) return
    if (uiPicker.recordAction === 'select') {
      const applied = await applyUiPickerSelect(false)
      if (!applied) return
    }
    const step = buildRecordedUiStep(uiPicker.pendingResult)
    if (!step) return
    uiPicker.targetForm.steps.push(step)
    syncUiStepIds(uiPicker.targetForm)
    uiPicker.pendingResult = null
    message.success('已添加步骤')
  }

  function appendUiPickerUtilityStep(action: 'wait' | 'screenshot') {
    if (!uiPicker.targetForm) return
    const step = defaultUiStep(action)
    step.value = action === 'wait' ? (uiPicker.inputText.trim() || '1000') : ''
    step.description = uiStepDescription(action)
    uiPicker.targetForm.steps.push(step)
    syncUiStepIds(uiPicker.targetForm)
    message.success('已添加步骤')
  }

  function removeUiPickerStep(index: number) {
    if (!uiPicker.targetForm) return
    uiPicker.targetForm.steps.splice(index, 1)
    syncUiStepIds(uiPicker.targetForm)
  }

  async function startUiPickerSession(form: UiCaseFormState, row: UiStepRow | null) {
    if (!form.environment_id) {
      message.warning('请先选择环境')
      return
    }
    if (!form.start_url.trim()) {
      message.warning('请先填写目标地址')
      return
    }
    await closeUiPicker(false)
    resetUiPickerState()
    uiPicker.targetRow = row
    uiPicker.targetForm = row ? null : form
    uiPicker.mode = row ? 'operate' : 'pick'
    uiPicker.status = 'starting'
    uiPicker.statusText = '启动中'
    uiPicker.message = '正在启动远程浏览器'
    uiPickerDialogVisible.value = true
    try {
      const { data } = await api.post('/ui-recorder/sessions', {
        environment_id: form.environment_id,
        start_url: form.start_url.trim()
      })
      applyUiPickerSession(data)
      uiPickerTimer = window.setInterval(pollUiPickerSession, 800)
      window.setTimeout(refreshUiPickerScreenshot, 800)
    } catch (error: any) {
      uiPicker.status = 'error'
      uiPicker.statusText = '异常'
      uiPicker.message = friendlyUiPickerMessage(error?.response?.data?.detail, '启动拾取会话失败')
    }
  }

  async function startUiElementPicker(form: UiCaseFormState, row: UiStepRow) {
    await startUiPickerSession(form, row)
  }

  async function startUiStepRecorder(form: UiCaseFormState) {
    await startUiPickerSession(form, null)
  }

  function applyUiPickerSession(data: any) {
    uiPicker.sessionId = data.id || uiPicker.sessionId
    uiPicker.status = data.status || ''
    uiPicker.statusText = uiPickerStatusText(uiPicker.status)
    uiPicker.message = friendlyUiPickerMessage(data.error, data.message || '')
    uiPicker.viewportWidth = Number(data.viewport?.width || uiPicker.viewportWidth || 1600)
    uiPicker.viewportHeight = Number(data.viewport?.height || uiPicker.viewportHeight || 900)
    const xpath = data.result?.xpath || ''
    const pickKey = uiPicker.targetRow ? xpath : `${uiPicker.recordAction}|${uiPicker.inputText.trim()}|${xpath}`
    if (xpath && pickKey !== uiPicker.lastPickKey) {
      uiPicker.xpath = xpath
      uiPicker.lastPickKey = pickKey
      uiPicker.summaryText = uiPickedSummary(data.result)
      if (uiPicker.targetRow) {
        uiPicker.targetRow.locator_type = 'xpath'
        uiPicker.targetRow.target = xpath
        message.success('元素已拾取，XPath 已回填')
      } else {
        uiPicker.pendingResult = data.result
        const summary = data.result?.summary || {}
        const selectedValue = selectedUiPickerOptionValue()
        if ((summary.tag === 'select' || uiPickerSelectOptions.value.length) && selectedValue) {
          uiPicker.inputText = selectedValue
        }
        refreshAutoUiRecordAction()
        message.success('元素已拾取，可点击“添加当前步骤”')
      }
    }
    if (['closed', 'error'].includes(uiPicker.status)) {
      stopUiPickerPolling()
    }
  }

  async function pollUiPickerSession() {
    if (!uiPicker.sessionId) return
    try {
      const { data } = await api.get(`/ui-recorder/sessions/${uiPicker.sessionId}`)
      applyUiPickerSession(data)
      if (['ready', 'picked'].includes(uiPicker.status) && !uiPicker.screenshotUrl && !uiPicker.loading) {
        refreshUiPickerScreenshot()
      }
    } catch (error: any) {
      uiPicker.status = 'error'
      uiPicker.statusText = '异常'
      uiPicker.message = error?.response?.data?.detail || '拾取会话已断开'
      stopUiPickerPolling()
    }
  }

  async function closeUiPicker(closeDialog = true) {
    stopUiPickerPolling()
    if (uiPicker.sessionId) {
      try {
        await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/close`)
      } catch {}
    }
    if (closeDialog) {
      uiPickerDialogVisible.value = false
    }
    resetUiPickerState()
  }

  async function refreshUiPickerScreenshot() {
    if (!uiPicker.sessionId || uiPicker.loading) return
    uiPicker.loading = true
    try {
      const { data } = await api.get(`/ui-recorder/sessions/${uiPicker.sessionId}/screenshot`, { responseType: 'blob' })
      const nextUrl = URL.createObjectURL(data)
      if (uiPicker.screenshotUrl) {
        URL.revokeObjectURL(uiPicker.screenshotUrl)
      }
      uiPicker.screenshotUrl = nextUrl
    } catch (error: any) {
      uiPicker.message = error?.response?.data?.detail || '刷新远程浏览器截图失败'
    } finally {
      uiPicker.loading = false
    }
  }

  function uiPickerPointFromEvent(event: MouseEvent) {
    const image = event.currentTarget as HTMLImageElement
    const rect = image.getBoundingClientRect()
    const x = ((event.clientX - rect.left) / rect.width) * uiPicker.viewportWidth
    const y = ((event.clientY - rect.top) / rect.height) * uiPicker.viewportHeight
    return { x, y }
  }

  async function handleUiPickerImageClick(event: MouseEvent) {
    if (!uiPicker.sessionId || uiPicker.loading) return
    const point = uiPickerPointFromEvent(event)
    try {
      if (uiPicker.mode === 'pick') {
        const { data } = await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/pick`, point)
        applyUiPickerSession(data)
      } else {
        const { data } = await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/click`, point)
        applyUiPickerSession(data)
      }
      await refreshUiPickerScreenshot()
    } catch (error: any) {
      uiPicker.message = error?.response?.data?.detail || '远程浏览器操作失败'
    }
  }

  async function typeUiPickerText() {
    if (!uiPicker.sessionId || !uiPicker.inputText) return
    try {
      const { data } = await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/type`, { text: uiPicker.inputText })
      applyUiPickerSession(data)
      if (uiPicker.targetRow) {
        uiPicker.inputText = ''
      }
      await refreshUiPickerScreenshot()
    } catch (error: any) {
      uiPicker.message = error?.response?.data?.detail || '远程浏览器输入失败'
    }
  }

  async function pressUiPickerKey(key: string) {
    if (!uiPicker.sessionId) return
    try {
      const { data } = await api.post(`/ui-recorder/sessions/${uiPicker.sessionId}/press`, { key })
      applyUiPickerSession(data)
      await refreshUiPickerScreenshot()
    } catch (error: any) {
      uiPicker.message = error?.response?.data?.detail || '远程浏览器按键失败'
    }
  }

  function uiCasePayload(form: UiCaseFormState) {
    if (!form.project_id) {
      message.warning('请选择项目')
      return null
    }
    if (!form.environment_id) {
      message.warning('请选择环境')
      return null
    }
    if (!form.name.trim()) {
      message.warning('请输入UI用例名称')
      return null
    }
    if (form.execution_mode === 'ai' && !form.test_goal.trim()) {
      message.warning('AI模式请填写测试目标')
      return null
    }
    const testData = parseJson(form.test_data_text, undefined)
    if (testData === undefined || Array.isArray(testData) || typeof testData !== 'object') {
      message.warning('测试数据必须是合法 JSON 对象')
      return null
    }
    return {
      project_id: form.project_id,
      environment_id: form.environment_id,
      name: form.name.trim(),
      start_url: form.start_url.trim(),
      description: form.description.trim(),
      execution_mode: form.execution_mode,
      test_goal: form.test_goal.trim(),
      test_data: testData,
      assertion_goal: form.assertion_goal.trim(),
      max_steps: Number(form.max_steps || 30),
      step_timeout_ms: Number(form.step_timeout_ms || 10000),
      allow_ai_actions: form.allow_ai_actions,
      status: form.status,
      browser_channel: form.browser_channel || 'chromium',
      headless: form.headless,
      wait_until: form.wait_until,
      wait_after_load_ms: Number(form.wait_after_load_ms || 0),
      steps: form.steps.map(({ action, locator_type, target, value, description }) => ({ action, locator_type, target, value, description }))
    }
  }

  async function createUiCase() {
    const payload = uiCasePayload(uiCaseForm)
    if (!payload) return
    await api.post('/ui-cases', payload)
    closeUiCaseEditorTab(UI_CASE_CREATE_TAB)
    resetUiCaseForm()
    message.success('UI用例已创建')
    await loadUiCases()
  }

  async function updateUiCase() {
    const payload = uiCasePayload(editUiCaseForm)
    if (!payload) return
    await api.put(`/ui-cases/${editUiCaseForm.id}`, payload)
    closeUiCaseEditorTab(`${UI_CASE_EDIT_PREFIX}${editUiCaseForm.id}`)
    resetEditUiCaseForm()
    message.success('UI用例已更新')
    await loadUiCases()
  }

  async function changeUiCaseMode(row: any, mode: any) {
    const nextMode = mode === 'ai' ? 'ai' : 'advanced'
    if (row.execution_mode === nextMode) return
    if (nextMode === 'ai' && !String(row.test_goal || '').trim()) {
      message.warning('切换到AI模式前，请先编辑用例填写测试目标')
      return
    }
    const payload = {
      project_id: row.project_id,
      environment_id: row.environment_id,
      name: row.name || '',
      start_url: row.start_url || '',
      description: row.description || '',
      execution_mode: nextMode,
      test_goal: row.test_goal || '',
      test_data: row.test_data || {},
      assertion_goal: row.assertion_goal || '',
      max_steps: Number(row.max_steps || 30),
      step_timeout_ms: Number(row.step_timeout_ms || 10000),
      allow_ai_actions: row.allow_ai_actions !== false,
      status: row.status || 'active',
      browser_channel: row.browser_channel || 'chromium',
      headless: row.headless !== false,
      wait_until: row.wait_until || 'networkidle',
      wait_after_load_ms: Number(row.wait_after_load_ms || 0),
      steps: (row.steps || []).map(({ action, locator_type, target, value, description }: any) => ({ action, locator_type, target, value, description }))
    }
    try {
      await api.put(`/ui-cases/${row.id}`, payload)
      row.execution_mode = nextMode
      message.success(`已切换为${nextMode === 'ai' ? 'AI模式' : '高级模式'}`)
      await loadUiCases()
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '切换用例模式失败')
      await loadUiCases()
    }
  }

  async function deleteUiCase(row: any) {
    await confirmAction(`确认删除 UI 用例 ${row.name}？`, '删除UI用例', { confirmButtonText: '删除' })
    await api.delete(`/ui-cases/${row.id}`)
    message.success('UI用例已删除')
    await loadUiCases()
  }

  async function executeUiCase(row: any) {
    const { data } = await api.post(`/ui-cases/${row.id}/execute`)
    row.last_task_id = data.id
    row.last_status = data.status || 'queued'
    message.success('UI执行任务已提交')
    await loadUiReports()
    pollUiExecution(row, data.id)
  }

  function uiExecutionCanStop(status: string) {
    return ['queued', 'running'].includes(String(status || ''))
  }

  async function stopUiExecution(row: any) {
    if (!row.last_task_id) {
      message.warning('暂无可停止的执行任务')
      return
    }
    await confirmAction('确认停止当前UI执行任务？已完成的步骤和截图会保留。', '停止UI执行', { confirmButtonText: '停止' })
    await api.post(`/ui-executions/${row.last_task_id}/stop`)
    row.last_status = 'stopped'
    message.success('已发送停止请求')
    await Promise.all([loadUiCases(), loadUiReports()])
  }

  async function stopUiExecutionFromDetail() {
    const taskId = uiExecutionDetail.task?.id
    if (!taskId) return
    await confirmAction('确认停止当前UI执行任务？已完成的步骤和截图会保留。', '停止UI执行', { confirmButtonText: '停止' })
    await api.post(`/ui-executions/${taskId}/stop`)
    const { data } = await api.get(`/ui-executions/${taskId}`)
    uiExecutionDetail.task = data.task
    uiExecutionDetail.results = data.results || []
    message.success('已发送停止请求')
    await Promise.all([loadUiCases(), loadUiReports()])
  }

  function pollUiExecution(row: any, taskId: number) {
    let attempts = 0
    const maxAttempts = 900
    const timer = window.setInterval(async () => {
      attempts += 1
      try {
        const { data } = await api.get(`/ui-executions/${taskId}`)
        row.last_status = data.task?.status || row.last_status
        if (uiExecutionDetailVisible.value && uiExecutionDetail.task?.id === taskId) {
          uiExecutionDetail.task = data.task
          uiExecutionDetail.results = data.results || []
        }
        const results = data.results || []
        const hasPersistedResult = results.some((item: any) => !String(item.id || '').startsWith('progress-'))
        const stillWritingProgress = Boolean(data.task?.summary?.ui_progress) && !hasPersistedResult
        if (['passed', 'failed', 'error', 'stopped'].includes(row.last_status) && !stillWritingProgress) {
          window.clearInterval(timer)
          await Promise.all([loadUiCases(), loadUiReports()])
          return
        }
        if (attempts >= maxAttempts) {
          window.clearInterval(timer)
          message.warning('UI执行仍在运行，已停止前端轮询，可稍后点击详情查看结果')
          await Promise.all([loadUiCases(), loadUiReports()])
        }
      } catch {
        if (attempts >= maxAttempts) {
          window.clearInterval(timer)
          await Promise.all([loadUiCases(), loadUiReports()])
        }
      }
    }, 1000)
  }

  async function openUiExecutionDetail(row: any) {
    if (!row.last_task_id) {
      message.warning('该UI用例暂无执行记录')
      return
    }
    const { data } = await api.get(`/ui-executions/${row.last_task_id}`)
    uiExecutionDetail.task = data.task
    uiExecutionDetail.results = data.results || []
    uiExecutionDetailVisible.value = true
  }

  function hasAiExecutionResult() {
    return uiExecutionDetail.results.some((item: any) => item.request_snapshot?.mode === 'ai')
  }

  function uiResultSteps(result: any) {
    const snapshot = result?.response_snapshot || {}
    return snapshot.agent_steps || snapshot.steps || []
  }

  function uiResultErrorMessage(result: any) {
    if (result?.error_message) return String(result.error_message)
    const snapshot = result?.response_snapshot || {}
    if (snapshot.message && ['failed', 'error'].includes(String(snapshot.status || result?.status || ''))) {
      return String(snapshot.message)
    }
    const failedStep = [...uiResultSteps(result)].reverse().find((item: any) => ['failed', 'error'].includes(String(item?.status || '')))
    return uiStepMessage(failedStep)
  }

  function uiStepMessage(row: any) {
    if (!row) return ''
    const modelError = row.model_error || {}
    const parts = [row.message || row.reason || row.description || row.error || '']
    if (modelError.hint) parts.push(modelError.hint)
    if (modelError.retry_count) parts.push(`已自动重试 ${Number(modelError.retry_count)} 次`)
    if (modelError.status_code) parts.push(`HTTP ${modelError.status_code}`)
    if (modelError.error && !parts.some(item => String(item).includes(String(modelError.error)))) parts.push(String(modelError.error))
    return parts.filter(Boolean).join('；') || '-'
  }

  function uiExecutionModeText(mode: string) {
    if (mode === 'ai') return 'AI模式'
    if (mode === 'advanced') return '高级模式'
    return mode || '-'
  }

  function uiBrowserChannelText(channel: string) {
    if (channel === 'chrome') return '本机 Chrome'
    if (channel === 'msedge') return '本机 Edge'
    return 'Chromium'
  }

  function uiTokenUsageText(usage: any, mode = 'ai') {
    if (mode !== 'ai') return '非AI模式不消耗Token'
    if (!usage || typeof usage !== 'object') return '暂无记录，重新执行AI模式后生成'
    const total = Number(usage.total_tokens || 0)
    const prompt = Number(usage.prompt_tokens || 0)
    const completion = Number(usage.completion_tokens || 0)
    const parts = [`总计 ${total}`, `输入 ${prompt}`, `输出 ${completion}`]
    if (Number(usage.reasoning_tokens || 0)) parts.push(`推理 ${Number(usage.reasoning_tokens)}`)
    if (Number(usage.cached_tokens || 0)) parts.push(`缓存 ${Number(usage.cached_tokens)}`)
    return parts.join(' / ')
  }

  function safeReportFilename(name: string) {
    return `${(name || 'UI测试报告').replace(/[\\/:*?"<>|]+/g, '_')}.html`
  }

  function downloadHtmlReport(filename: string, html: string) {
    const blob = new Blob([html || '<h1>报告尚未生成</h1>'], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  function exportUiExecutionReport() {
    const task = uiExecutionDetail.task
    if (!task?.report_html) {
      message.warning('报告尚未生成，请执行完成后再导出')
      return
    }
    downloadHtmlReport(safeReportFilename(task.target_name || `UI测试报告_${task.id || ''}`), task.report_html)
  }

  async function solidifyUiExecution() {
    const taskId = uiExecutionDetail.task?.id
    if (!taskId) return
    await confirmAction('确认把本次 AI 执行轨迹固化为高级步骤？固化后用例会切换到高级模式，可继续手工调整。', '固化UI流程')
    await api.post(`/ui-executions/${taskId}/solidify`)
    message.success('已固化为高级步骤')
    uiExecutionDetailVisible.value = false
    await loadUiCases()
  }

  async function loadAiSetting(preferredId?: number) {
    const { data } = await api.get('/ai-settings')
    aiSettings.value = data.items || []
    const preferred = preferredId ? aiSettings.value.find(item => item.id === preferredId) : null
    editAiSetting(preferred || (data.id ? data : aiSettings.value[0]))
  }

  async function openAiSettingDialog() {
    await loadAiSetting()
    aiSettingDialogVisible.value = true
  }

  function resetAiSettingForm() {
    aiSettingForm.id = undefined
    aiSettingForm.name = ''
    aiSettingForm.provider_url = ''
    aiSettingForm.model_name = ''
    aiSettingForm.api_key = ''
    aiSettingForm.status = 'active'
    aiSettingForm.is_default = aiSettings.value.length === 0
    aiSettingForm.description = ''
  }

  function editAiSetting(row: any) {
    if (!row) {
      resetAiSettingForm()
      return
    }
    aiSettingForm.id = row.id
    aiSettingForm.name = row.name || ''
    aiSettingForm.provider_url = row.provider_url || ''
    aiSettingForm.model_name = row.model_name || ''
    aiSettingForm.api_key = row.api_key || ''
    aiSettingForm.status = row.status || 'disabled'
    aiSettingForm.is_default = row.is_default === true
    aiSettingForm.description = row.description || ''
  }

  async function saveAiSetting() {
    const { data } = await api.put('/ai-settings', {
      id: aiSettingForm.id,
      name: aiSettingForm.name.trim(),
      provider_url: aiSettingForm.provider_url.trim(),
      model_name: aiSettingForm.model_name.trim(),
      api_key: aiSettingForm.api_key === '******' ? '' : aiSettingForm.api_key,
      status: aiSettingForm.status,
      is_default: aiSettingForm.is_default,
      description: aiSettingForm.description.trim()
    })
    message.success('AI配置已保存')
    await loadAiSetting(data.id)
  }

  async function setDefaultAiSetting(row: any) {
    await api.post(`/ai-settings/${row.id}/default`)
    message.success('默认AI配置已更新')
    await loadAiSetting()
  }

  async function deleteAiSetting(row: any) {
    await confirmAction(`确认删除 AI 配置 ${row.name || row.id}？`, '删除AI配置', { confirmButtonText: '删除' })
    await api.delete(`/ai-settings/${row.id}`)
    message.success('AI配置已删除')
    await loadAiSetting()
  }

  async function testAiSetting() {
    aiSettingTesting.value = true
    try {
      const { data } = await api.post('/ai-settings/test', {
        id: aiSettingForm.id,
        name: aiSettingForm.name.trim(),
        provider_url: aiSettingForm.provider_url.trim(),
        model_name: aiSettingForm.model_name.trim(),
        api_key: aiSettingForm.api_key === '******' ? '' : aiSettingForm.api_key,
        status: aiSettingForm.status,
        is_default: aiSettingForm.is_default,
        description: aiSettingForm.description.trim()
      })
      message.success(data?.message || '连接成功')
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'AI连接失败')
    } finally {
      aiSettingTesting.value = false
    }
  }

  function uiArtifactUrl(path: string) {
    const filename = String(path || '').split(/[\\/]/).pop()
    if (!filename) return ''
    if (!uiArtifactObjectUrls[filename] && !uiArtifactLoading.has(filename) && !uiArtifactFailed.has(filename)) {
      loadUiArtifact(filename)
    }
    return uiArtifactObjectUrls[filename] || ''
  }

  async function loadUiArtifact(filename: string) {
    uiArtifactLoading.add(filename)
    try {
      const { data } = await api.get(`/ui-artifacts/${encodeURIComponent(filename)}`, { responseType: 'blob' })
      if (uiArtifactObjectUrls[filename]) {
        URL.revokeObjectURL(uiArtifactObjectUrls[filename])
      }
      uiArtifactObjectUrls[filename] = URL.createObjectURL(data)
    } catch {
      uiArtifactFailed.add(filename)
    } finally {
      uiArtifactLoading.delete(filename)
    }
  }
  
  function addMockHeaderRow() {
  mockForm.headerRows.push(nextApiRow('', ''))
}

function removeMockHeaderRow(index: number) {
  mockForm.headerRows.splice(index, 1)
}

function addEditMockHeaderRow() {
  editMockForm.headerRows.push(nextApiRow('', ''))
}

function removeEditMockHeaderRow(index: number) {
  editMockForm.headerRows.splice(index, 1)
}

function mockBodyPlaceholder(format: MockBodyFormat) {
  if (format === 'xml') return '<RESPONSE>\n  <STATUS>0</STATUS>\n</RESPONSE>'
  if (format === 'text') return 'success'
  return '{\n  "code": 0,\n  "message": "success"\n}'
}

function formatMockBody(form: MockFormState) {
  if (form.body_format === 'xml') {
    try {
      form.response_body = formatXmlTextPreservingTags(form.response_body)
      message.success('XML 已格式化')
    } catch {
      message.warning('XML 格式不完整，已保留原内容')
    }
    return
  }
  if (form.body_format === 'text') {
    message.info('文本格式无需格式化')
    return
  }
  const parsed = parseJson(form.response_body, undefined)
  if (parsed === undefined) {
    message.warning('响应Body必须是合法 JSON')
    return
  }
  form.response_body = JSON.stringify(parsed, null, 2)
  message.success('JSON 已格式化')
}

function mockPayload(form: MockFormState) {
  const projectId = form.project_id
  const environmentId = form.environment_id
  const name = form.name.trim()
  const path = form.path.trim()
  const statusCode = Number(form.status_code || 0)
  const delayMs = Number(form.delay_ms || 0)
  if (!projectId) {
    message.warning('请选择项目')
    return null
  }
  if (!environmentId) {
    message.warning('请选择环境')
    return null
  }
  if (!name) {
    message.warning('请输入Mock名称')
    return null
  }
  if (!path) {
    message.warning('请输入Mock路径')
    return null
  }
  if (statusCode < 100 || statusCode > 599) {
    message.warning('HTTP状态码必须在100-599之间')
    return null
  }
  return {
    project_id: projectId,
    environment_id: environmentId,
    name,
    method: form.method,
    path,
    status: form.status,
    status_code: statusCode,
    delay_ms: delayMs,
      headers: rowsToObject(form.headerRows),
      response_body: form.response_body,
      body_format: form.body_format,
      sm3_enabled: form.sm3_enabled,
      description: form.description.trim()
    }
}

async function refreshMocksAfterChange() {
  await loadMocks()
}

async function createMock() {
  const payload = mockPayload(mockForm)
  if (!payload) return
  try {
    await api.post('/mocks', payload)
    createMockDialogVisible.value = false
    resetMockForm()
    message.success('Mock已创建')
    await refreshMocksAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Mock创建失败')
  }
}

async function updateMock() {
  const payload = mockPayload(editMockForm)
  if (!payload) return
  try {
    await api.put(`/mocks/${editMockForm.id}`, payload)
    editMockDialogVisible.value = false
    resetEditMockForm()
    message.success('Mock已更新')
    await refreshMocksAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Mock更新失败')
  }
}

async function toggleMockStatus(row: any) {
  try {
    await api.put(`/mocks/${row.id}`, {
      project_id: row.project_id,
      environment_id: row.environment_id,
      name: row.name,
      method: row.method,
      path: row.path,
      status: row.status === 'active' ? 'disabled' : 'active',
      status_code: row.status_code,
      delay_ms: row.delay_ms,
        headers: row.headers || {},
        response_body: row.response_body || '',
        body_format: row.body_format || 'json',
        sm3_enabled: !!row.sm3_enabled,
        description: row.description || ''
      })
    message.success(row.status === 'active' ? 'Mock已禁用' : 'Mock已启用')
    await refreshMocksAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Mock状态更新失败')
  }
}

async function deleteMock(row: any) {
  try {
    await confirmAction('确认删除该Mock规则吗？', '删除Mock', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/mocks/${row.id}`)
  message.success('Mock已删除')
  await refreshMocksAfterChange()
}

async function refreshApisAfterChange() {
  await Promise.all([
    api.get('/apis').then(r => apis.value = r.data),
    loadApis()
  ])
}

async function refreshApisAfterDelete() {
  await refreshApisAfterChange()
  if (apiList.value.length === 0 && apiPagination.page > 1) {
    apiPagination.page -= 1
    await loadApis()
  }
}

function apiNameExists(projectId: number, name: string, apiId?: number) {
  return apis.value.some(item =>
    item.project_id === projectId &&
    item.name === name &&
    item.id !== apiId
  )
}

let apiRowId = 1
let caseAssertionRowId = 1
let caseExtractorRowId = 1
const contentTypes: Record<ApiEditor['bodyFormat'], string> = {
  json: 'application/json',
  xml: 'application/xml',
  'x-www-form-data': 'application/x-www-form-urlencoded'
}

function nextApiRow(key = '', value = ''): KeyValueRow {
  return { id: apiRowId++, key, value }
}

function assertionPartsFromType(type: string): { target: AssertionTarget; check: AssertionCheck } {
  const mapping: Record<string, { target: AssertionTarget; check: AssertionCheck }> = {
    status_code: { target: 'status', check: 'equal' },
    duration_lt: { target: 'duration', check: 'lt' },
    jsonpath_equal: { target: 'jsonpath', check: 'equal' },
    jsonpath_exists: { target: 'jsonpath', check: 'exists' },
    jsonpath_not_empty: { target: 'jsonpath', check: 'not_empty' },
    xmlpath_equal: { target: 'xmlpath', check: 'equal' },
    xmlpath_exists: { target: 'xmlpath', check: 'exists' },
    xmlpath_not_empty: { target: 'xmlpath', check: 'not_empty' },
    body_contains: { target: 'text', check: 'contains' }
  }
  return mapping[type] || mapping.status_code
}

function assertionTypeFromParts(target: AssertionTarget, check: AssertionCheck) {
  if (target === 'status') return 'status_code'
  if (target === 'duration') return 'duration_lt'
  if (target === 'text') return 'body_contains'
  return `${target}_${check}`
}

function defaultAssertionCheck(target: AssertionTarget): AssertionCheck {
  return assertionChecks[target][0].value as AssertionCheck
}

function defaultAssertionExpected(target: AssertionTarget, check: AssertionCheck) {
  if (target === 'status') return 200
  if (target === 'duration') return 1000
  if (['exists', 'not_empty'].includes(check)) return ''
  return ''
}

function nextCaseAssertionRow(type = 'status_code', path = '', expected?: string | number | null): CaseAssertionRow {
  const { target, check } = assertionPartsFromType(type)
  return {
    id: caseAssertionRowId++,
    type,
    target,
    check,
    path,
    expected: expected ?? defaultAssertionExpected(target, check)
  }
}

function nextCaseExtractorRow(name = '', path = '', source: CaseExtractorRow['source'] = 'jsonpath'): CaseExtractorRow {
  return { id: caseExtractorRowId++, name, path, source }
}

function defaultHeaderRows() {
  return [
    nextApiRow('Connection', 'keep-alive'),
    nextApiRow('Accept-Encoding', 'gzip, deflate, br'),
    nextApiRow('Content-Type', contentTypes.json)
  ]
}

function objectToRows(value: any, fallback: KeyValueRow[] = []) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return fallback
  }
  return Object.entries(value).map(([key, rowValue]) => nextApiRow(key, String(rowValue ?? '')))
}

function mergeDefaultHeaders(rows: KeyValueRow[]) {
  const merged = [...rows]
  defaultHeaderRows().forEach(defaultRow => {
    if (!merged.some(row => row.key.trim().toLowerCase() === defaultRow.key.toLowerCase())) {
      merged.push(defaultRow)
    }
  })
  return merged
}

function bodyFormatFromApi(row: any): ApiEditor['bodyFormat'] {
  const format = row?.body?.format
  if (format === 'xml' || format === 'x-www-form-data') {
    return format
  }
  return 'json'
}

function bodyTemplateFromApi(row: any) {
  const template = row?.body?.template
  return typeof template === 'string' ? template : ''
}

function selectedCaseApi() {
  return apis.value.find(item => item.id === caseForm.api_id)
}

function emptyBodyForFormat(format: ApiEditor['bodyFormat']) {
  return format === 'xml' ? '<request>\n</request>' : '{}'
}

function isCaseBodyPristine() {
  const body = caseForm.bodyText.trim()
  return body === '' || body === '{}' || body === '<request>\n</request>' || body === '<request>\\n</request>'
}

function syncCaseBodyFormatFromApi(resetEmptyBody = false) {
  const api = selectedCaseApi()
  const format = bodyFormatFromApi(api)
  const template = bodyTemplateFromApi(api).trim()
  caseForm.bodyFormat = format
  if (resetEmptyBody && isCaseBodyPristine()) {
    caseForm.bodyText = template || emptyBodyForFormat(format)
  }
}

function reuseCaseBodyTemplate() {
  const api = selectedCaseApi()
  if (!api) {
    message.warning('请先选择接口')
    return
  }
  const template = bodyTemplateFromApi(api).trim()
  if (!template) {
    message.warning('当前接口未配置请求体模板')
    return
  }
  caseForm.bodyFormat = bodyFormatFromApi(api)
  caseForm.bodyText = template
  message.success('已复用接口请求体模板')
}

function formatXmlText(text: string) {
  const source = text.trim()
  if (!source) return ''
  return formatXmlTextPreservingTags(source)
  const parser = new DOMParser()
  const document = parser.parseFromString(source, 'application/xml')
  if (document.getElementsByTagName('parsererror').length) {
    throw new Error('XML 解析失败')
  }
  return formatXmlNode(document.documentElement, 0)
}

function formatXmlTextPreservingTags(text: string) {
  const source = text.trim()
  if (!source) return ''
  const tokens = source.match(/<!\[CDATA\[[\s\S]*?\]\]>|<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<[^>]+>|[^<]+/g)
  if (!tokens) {
    throw new Error('Invalid XML')
  }
  const rows: string[] = []
  const stack: string[] = []
  let level = 0
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index].trim()
    if (!token) continue
    if (!token.startsWith('<')) {
      rows.push(`${xmlIndent(level)}${token}`)
      continue
    }
    if (token.startsWith('<?') || token.startsWith('<!--') || token.startsWith('<![CDATA[')) {
      rows.push(`${xmlIndent(level)}${token}`)
      continue
    }
    if (token.startsWith('</')) {
      const closingTag = token.match(/^<\/([A-Za-z_][\w.:-]*)\s*>$/)?.[1]
      const expectedTag = stack.pop()
      if (!closingTag || expectedTag !== closingTag) {
        throw new Error('Invalid XML')
      }
      level = Math.max(level - 1, 0)
      rows.push(`${xmlIndent(level)}${token}`)
      continue
    }
    const tagName = token.match(/^<([A-Za-z_][\w.:-]*)\b/)?.[1]
    if (!tagName) {
      throw new Error('Invalid XML')
    }
    if (token.endsWith('/>')) {
      rows.push(`${xmlIndent(level)}${token}`)
      continue
    }
    let nextIndex = index + 1
    while (nextIndex < tokens.length && !tokens[nextIndex].trim()) {
      nextIndex += 1
    }
    const nextToken = tokens[nextIndex]?.trim()
    const closeToken = tokens[nextIndex + 1]?.trim()
    if (nextToken === `</${tagName}>`) {
      const selfClosing = token.replace(/>$/, '/>')
      rows.push(`${xmlIndent(level)}${selfClosing}`)
      index = nextIndex
      continue
    }
    if (nextToken && !nextToken.startsWith('<') && closeToken === `</${tagName}>`) {
      rows.push(`${xmlIndent(level)}${token}${nextToken}</${tagName}>`)
      index += 2
      continue
    }
    rows.push(`${xmlIndent(level)}${token}`)
    stack.push(tagName)
    level += 1
  }
  if (stack.length) {
    throw new Error('Invalid XML')
  }
  return rows.join('\n')
}

function splitFirstXmlDocument(text: string) {
  const source = text.trim()
  const match = source.match(/<([A-Za-z_][\w.:-]*)\b[^>]*>/)
  if (!match || match.index === undefined) return null
  const startTag = match[0]
  if (startTag.trim().endsWith('/>')) {
    return {
      xml: source.slice(0, match.index + startTag.length),
      rest: source.slice(match.index + startTag.length).trim()
    }
  }
  const closeTag = `</${match[1]}>`
  const closeIndex = source.indexOf(closeTag, match.index + startTag.length)
  if (closeIndex < 0) return null
  const endIndex = closeIndex + closeTag.length
  return {
    xml: source.slice(0, endIndex),
    rest: source.slice(endIndex).trim()
  }
}

function formatXmlPayloadText(text: string) {
  try {
    return formatXmlTextPreservingTags(text)
  } catch {
    const split = splitFirstXmlDocument(text)
    if (!split) return text
    try {
      const formattedXml = formatXmlTextPreservingTags(split.xml)
      return split.rest ? `${formattedXml}\n${split.rest}` : formattedXml
    } catch {
      return text
    }
  }
}

function xmlIndent(level: number) {
  return '    '.repeat(level)
}

function xmlAttributes(element: Element) {
  return Array.from(element.attributes)
    .map(attr => ` ${attr.name}="${attr.value}"`)
    .join('')
}

function formatXmlNode(node: Node, level: number): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return `${xmlIndent(level)}${node.textContent?.trim() || ''}`
  }
  if (node.nodeType === Node.CDATA_SECTION_NODE) {
    return `${xmlIndent(level)}<![CDATA[${node.textContent || ''}]]>`
  }
  if (node.nodeType === Node.COMMENT_NODE) {
    return `${xmlIndent(level)}<!--${node.textContent || ''}-->`
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return ''
  }
  const element = node as Element
  const tag = element.tagName
  const attrs = xmlAttributes(element)
  const children = Array.from(element.childNodes)
    .filter(child => child.nodeType !== Node.TEXT_NODE || Boolean(child.textContent?.trim()))
  if (children.length === 0) {
    return `${xmlIndent(level)}<${tag}${attrs}></${tag}>`
  }
  if (children.length === 1 && children[0].nodeType === Node.TEXT_NODE) {
    return `${xmlIndent(level)}<${tag}${attrs}>${children[0].textContent?.trim() || ''}</${tag}>`
  }
  const inner = children
    .map(child => formatXmlNode(child, level + 1))
    .filter(Boolean)
    .join('\n')
  return `${xmlIndent(level)}<${tag}${attrs}>\n${inner}\n${xmlIndent(level)}</${tag}>`
}

function formatCaseBody() {
  if (caseForm.bodyFormat === 'xml') {
    try {
      caseForm.bodyText = formatXmlTextPreservingTags(caseForm.bodyText)
      message.success('XML 已格式化')
    } catch {
      message.warning('XML 格式不完整，已保留原内容')
    }
    return
  }
  const parsed = parseJsonAllowVariables(caseForm.bodyText, undefined)
  if (parsed === undefined) {
    message.warning(caseForm.bodyFormat === 'x-www-form-data' ? '表单 Body 必须是合法 JSON 对象' : 'Body 必须是合法 JSON')
    return
  }
  caseForm.bodyText = JSON.stringify(parsed, null, 2)
  message.success('JSON 已格式化')
}

function formatBodyText(text: string, format: ApiEditor['bodyFormat']) {
  if (format === 'xml') {
    return formatXmlTextPreservingTags(text)
  }
  const parsed = parseJson(text, undefined)
  if (parsed === undefined) {
    throw new Error('Invalid JSON')
  }
  if (format === 'x-www-form-data' && (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))) {
    throw new Error('Invalid form JSON')
  }
  return JSON.stringify(parsed, null, 2)
}

function apiBodyTemplatePlaceholder(editor: ApiEditor) {
  if (editor.bodyFormat === 'xml') return '<request>\n    <token>${token}</token>\n</request>'
  if (editor.bodyFormat === 'x-www-form-data') return '{\n    "username": "${username}",\n    "password": "${password}"\n}'
  return '{\n    "token": "${token}"\n}'
}

function formatApiBodyTemplate(editor: ApiEditor) {
  if (!editor.bodyTemplate.trim()) {
    message.warning('请先输入请求体模板')
    return
  }
  try {
    editor.bodyTemplate = formatBodyText(editor.bodyTemplate, editor.bodyFormat)
    markApiEditorDirty(editor)
    message.success(editor.bodyFormat === 'xml' ? 'XML 已格式化' : 'JSON 已格式化')
  } catch {
    message.warning(editor.bodyFormat === 'xml' ? 'XML 格式不完整，已保留原内容' : '模板必须是合法 JSON')
  }
}

function insertTextareaTab(target: HTMLTextAreaElement, value: string, update: (next: string) => void) {
  const start = target.selectionStart
  const end = target.selectionEnd
  const indent = '  '
  update(`${value.slice(0, start)}${indent}${value.slice(end)}`)
  requestAnimationFrame(() => {
    target.selectionStart = start + indent.length
    target.selectionEnd = start + indent.length
  })
}

function insertCaseBodyTab(event: KeyboardEvent) {
  const target = event.target as HTMLTextAreaElement | null
  if (!target) return
  insertTextareaTab(target, caseForm.bodyText, next => { caseForm.bodyText = next })
}

function insertApiBodyTemplateTab(event: KeyboardEvent, editor: ApiEditor) {
  const target = event.target as HTMLTextAreaElement | null
  if (!target) return
  insertTextareaTab(target, editor.bodyTemplate, next => {
    editor.bodyTemplate = next
    markApiEditorDirty(editor)
  })
}

function createEmptyApiEditor(): ApiEditor {
  const editor: ApiEditor = {
    tabName: 'api-create',
    label: '新增接口',
    mode: 'create',
    project_id: undefined,
    name: '',
    description: '',
    method: 'GET',
    path: '',
    bodyFormat: 'json',
    bodyTemplate: '',
    activePanel: '',
    queryRows: [],
    headerRows: defaultHeaderRows(),
    preScript: '',
    encryption: {
      enabled: false,
      mode: 'none',
      encryptRequest: false,
      decryptResponse: false,
      sm3Signature: false,
    },
    auth: defaultApiAuth(),
    dirty: false
  }
  return editor
}

function defaultApiAuth(): ApiAuth {
  return {
    type: 'none',
    addTo: 'headers',
    headerName: 'Authorization',
    headerPrefix: 'Bearer',
    token: '',
    username: '',
    password: '',
    apiKeyName: '',
    apiKeyValue: '',
    tokenUrl: '',
    grantType: 'client_credentials',
    clientId: '',
    clientSecret: '',
    scope: '',
    audience: '',
    clientAuthentication: 'body',
    verifyTls: true,
    currentToken: '',
    loading: false,
  }
}

function encryptionFromApi(row: any): ApiEncryption {
  const encryption = row.encryption || {}
  const sm3Signature = Boolean(encryption.sm3_signature)
  const enabled = encryption.mode === 'rsa_aes_sm3'
  return {
    enabled,
    mode: encryption.mode === 'rsa_aes_sm3' ? 'rsa_aes_sm3' : 'none',
    encryptRequest: Boolean(encryption.encrypt_request),
    decryptResponse: Boolean(encryption.decrypt_response),
    sm3Signature,
  }
}

function authFromApi(row: any): ApiAuth {
  const auth = row.auth || {}
  return {
    ...defaultApiAuth(),
    type: auth.type || 'none',
    addTo: auth.add_to || 'headers',
    headerName: auth.header_name || 'Authorization',
    headerPrefix: auth.header_prefix || 'Bearer',
    token: auth.token || '',
    username: auth.username || '',
    password: auth.password || '',
    apiKeyName: auth.api_key_name || '',
    apiKeyValue: auth.api_key_value || '',
    tokenUrl: auth.token_url || '',
    grantType: auth.grant_type || 'client_credentials',
    clientId: auth.client_id || '',
    clientSecret: auth.client_secret || '',
    scope: auth.scope || '',
    audience: auth.audience || '',
    clientAuthentication: auth.client_authentication || 'body',
    verifyTls: auth.verify_tls !== false,
  }
}

function createEditApiEditor(row: any): ApiEditor {
  const savedHeaderRows = objectToRows(row.headers)
  const editor: ApiEditor = {
    tabName: `api-edit-${row.id}`,
    label: '编辑接口',
    mode: 'edit',
    apiId: row.id,
    project_id: row.project_id,
    name: row.name || '',
    description: row.description || '',
    method: row.method || 'GET',
    path: row.path || '',
    bodyFormat: bodyFormatFromApi(row),
    bodyTemplate: bodyTemplateFromApi(row),
    activePanel: '',
    queryRows: objectToRows(row.query),
    headerRows: mergeDefaultHeaders(savedHeaderRows),
    preScript: row.pre_script || '',
    encryption: encryptionFromApi(row),
    auth: authFromApi(row),
    dirty: false
  }
  syncApiEditorContentType(editor, false)
  return editor
}

function openCreateApiDialog() {
  if (!apiEditors['api-create']) {
    apiEditors['api-create'] = createEmptyApiEditor()
  }
  openRuntimeTab({ name: 'api-create', label: '新增接口', closable: true })
}

function openEditApiDialog(row: any) {
  const tabName = `api-edit-${row.id}`
  if (!apiEditors[tabName]) {
    apiEditors[tabName] = createEditApiEditor(row)
  }
  openRuntimeTab({ name: tabName, label: '编辑接口', closable: true })
}

function markApiEditorDirty(editor: ApiEditor) {
  editor.dirty = true
}

function changeApiEditorProject(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function apiEditorEnvironment(editor: ApiEditor) {
  return environments.value.find(item => item.project_id === editor.project_id)
}

function environmentBaseUrl(environment: any) {
  if (!environment) return ''
  const baseUrl = String(environment.base_url || '').trim().replace(/\/+$/, '')
  const protocol = environment.protocol || 'http'
  const defaultPort = protocol === 'http' ? 80 : 443
  const port = environment.port && Number(environment.port) !== defaultPort ? `:${environment.port}` : ''
  return /^https?:\/\//i.test(baseUrl) ? baseUrl : `${protocol}://${baseUrl.replace(/^\/+/, '')}${port}`
}

function joinUrl(root: string, path: string) {
  if (!root) return ''
  if (/^https?:\/\//i.test(String(path || '').trim())) {
    return String(path || '').trim()
  }
  return `${root.replace(/\/+$/, '')}/${String(path || '').replace(/^\/+/, '')}`
}

function urlOrigin(url: string) {
  try {
    return new URL(url).origin
  } catch {
    return ''
  }
}

function apiEditorAuthRoot(editor: ApiEditor) {
  const path = editor.path.trim()
  if (/^https?:\/\//i.test(path)) {
    return urlOrigin(path)
  }
  return environmentBaseUrl(apiEditorEnvironment(editor))
}

function apiEditorScopeUrl(editor: ApiEditor) {
  const path = editor.path.trim()
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) {
    return path
  }
  return joinUrl(environmentBaseUrl(apiEditorEnvironment(editor)), path)
}

function generateApiAuthUrls(editor: ApiEditor, force = false, dirty = true) {
  if (editor.auth.type !== 'oauth2_client_credentials') return
  const root = apiEditorAuthRoot(editor)
  const scope = apiEditorScopeUrl(editor)
  let changed = false
  if ((force || !editor.auth.tokenUrl) && root) {
    editor.auth.tokenUrl = joinUrl(root, '/OAuth/Oauth/Token')
    changed = true
  }
  if ((force || !editor.auth.scope) && scope) {
    editor.auth.scope = scope
    changed = true
  }
  if (dirty && changed) {
    markApiEditorDirty(editor)
  }
}

function applyApiAuthDefaults(editor: ApiEditor) {
  if (editor.auth.type !== 'oauth2_client_credentials') return
  generateApiAuthUrls(editor, false, false)
}

function changeApiAuthType(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function changeApiEditorPath(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function syncApiEditorContentType(editor: ApiEditor, dirty = true) {
  const row = editor.headerRows.find(item => item.key.trim().toLowerCase() === 'content-type')
  if (row) {
    row.value = contentTypes[editor.bodyFormat]
  } else {
    editor.headerRows.push(nextApiRow('Content-Type', contentTypes[editor.bodyFormat]))
  }
  if (dirty) {
    markApiEditorDirty(editor)
  }
}

function changeApiEditorBodyFormat(editor: ApiEditor) {
  syncApiEditorContentType(editor)
}

function addApiEditorRow(rows: KeyValueRow[], key = '') {
  rows.push(nextApiRow(key, ''))
  if (activeApiEditor.value) {
    markApiEditorDirty(activeApiEditor.value)
  }
}

function removeApiEditorRow(rows: KeyValueRow[], index: number, editor: ApiEditor) {
  rows.splice(index, 1)
  markApiEditorDirty(editor)
}

function rowsToObject(rows: KeyValueRow[]) {
  return rows.reduce<Record<string, string>>((result, row) => {
    const key = row.key.trim()
    if (key) {
      result[key] = row.value
    }
    return result
  }, {})
}

function upsertApiEditorHeader(editor: ApiEditor, key: string, value: string) {
  const headerKey = key.trim()
  if (!headerKey) return
  const row = editor.headerRows.find(item => item.key.trim().toLowerCase() === headerKey.toLowerCase())
  if (row) {
    row.value = value
  } else {
    editor.headerRows.push(nextApiRow(headerKey, value))
  }
  markApiEditorDirty(editor)
}

function upsertApiEditorQuery(editor: ApiEditor, key: string, value: string) {
  const queryKey = key.trim()
  if (!queryKey) return
  const row = editor.queryRows.find(item => item.key.trim() === queryKey)
  if (row) {
    row.value = value
  } else {
    editor.queryRows.push(nextApiRow(queryKey, value))
  }
  markApiEditorDirty(editor)
}

function apiPayload(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  const headers = rowsToObject(editor.headerRows)
  return {
    project_id: editor.project_id,
    name: editor.name.trim(),
    description: editor.description.trim(),
    method: editor.method,
    path: editor.path.trim(),
    headers,
    query: rowsToObject(editor.queryRows),
    body: { format: editor.bodyFormat, template: editor.bodyTemplate },
    pre_script: editor.preScript,
    encryption: {
      mode: editor.encryption.enabled ? 'rsa_aes_sm3' : 'none',
      encrypt_request: editor.encryption.enabled && editor.encryption.encryptRequest,
      decrypt_response: editor.encryption.enabled && editor.encryption.decryptResponse,
      client_header: 'appKey',
      sm3_signature: editor.encryption.sm3Signature
    },
    auth: {
      type: editor.auth.type,
      add_to: editor.auth.addTo,
      header_name: editor.auth.headerName || 'Authorization',
      header_prefix: editor.auth.headerPrefix || 'Bearer',
      token: editor.auth.token,
      username: editor.auth.username,
      password: editor.auth.password,
      api_key_name: editor.auth.apiKeyName,
      api_key_value: editor.auth.apiKeyValue,
      token_url: editor.auth.tokenUrl,
      grant_type: editor.auth.grantType || 'client_credentials',
      client_id: editor.auth.clientId,
      client_secret: editor.auth.clientSecret,
      scope: editor.auth.scope,
      audience: editor.auth.audience,
      client_authentication: editor.auth.clientAuthentication,
      verify_tls: editor.auth.verifyTls
    }
  }
}

async function getApiEditorAccessToken(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  const environment = apiEditorEnvironment(editor)
  if (!environment?.id) {
    message.warning('请先选择存在环境配置的项目')
    return
  }
  if (!editor.auth.tokenUrl) {
    message.warning('请输入 Access Token URL')
    return
  }
  if (!editor.auth.clientId) {
    message.warning('请输入 Client ID')
    return
  }
  editor.auth.loading = true
  try {
    const { data } = await api.post('/apis/auth/token', {
      environment_id: environment.id,
      path: editor.path.trim() || '/',
      auth: apiPayload(editor).auth
    })
    editor.auth.currentToken = data.access_token || ''
    if (editor.auth.currentToken) {
      const headerName = editor.auth.headerName || 'Authorization'
      const headerPrefix = editor.auth.headerPrefix || 'Bearer'
      if (editor.auth.addTo === 'query') {
        upsertApiEditorQuery(editor, 'access_token', editor.auth.currentToken)
        editor.activePanel = 'query'
      } else {
        upsertApiEditorHeader(editor, headerName, `${headerPrefix} ${editor.auth.currentToken}`.trim())
        editor.activePanel = 'headers'
      }
    }
    message.success('Access Token 获取成功')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Access Token 获取失败')
  } finally {
    editor.auth.loading = false
  }
}

function validateApiEditor(editor: ApiEditor) {
  const payload = apiPayload(editor)
  if (!payload.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!payload.name) {
    message.warning('请输入接口名称')
    return null
  }
  if (!payload.path) {
    message.warning('请输入接口路径')
    return null
  }
  if (apiNameExists(payload.project_id, payload.name, editor.apiId)) {
    message.warning('接口名称已存在')
    return null
  }
  return payload
}

async function saveApiEditor(editor: ApiEditor, closeAfterSave = false) {
  const payload = validateApiEditor(editor)
  if (!payload) {
    return false
  }
  try {
    if (editor.mode === 'edit') {
      await api.put(`/apis/${editor.apiId}`, payload)
      message.success('接口已更新')
    } else {
      const { data } = await api.post('/apis', payload)
      message.success('接口已创建')
      if (!closeAfterSave) {
        promoteCreatedApiEditor(editor, data.id)
      }
    }
    editor.dirty = false
    await refreshApisAfterChange()
    if (closeAfterSave) {
      closeApiEditorSilently(editor.tabName)
    }
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '接口保存失败')
    return false
  }
}

function promoteCreatedApiEditor(editor: ApiEditor, apiId: number) {
  const oldTabName = editor.tabName
  const newTabName = `api-edit-${apiId}`
  delete apiEditors[oldTabName]
  editor.tabName = newTabName
  editor.label = '编辑接口'
  editor.mode = 'edit'
  editor.apiId = apiId
  apiEditors[newTabName] = editor
  const tab = openedTabs.value.find(item => item.name === oldTabName)
  if (tab) {
    tab.name = newTabName
    tab.label = editor.label
  }
  active.value = newTabName
  saveTabs()
}

function closeApiEditorSilently(tabName: string) {
  delete apiEditors[tabName]
  removeTab(tabName)
}

async function requestCloseApiEditor(editor: ApiEditor) {
  if (!editor.dirty) {
    closeApiEditorSilently(editor.tabName)
    return
  }
  try {
    await confirmAction('当前接口内容尚未保存，是否保存后关闭？', '关闭接口', {
      confirmButtonText: '保存并关闭',
      cancelButtonText: '不保存关闭',
      distinguishCancelAndClose: true,
      type: 'warning'
    })
    await saveApiEditor(editor, true)
  } catch (action) {
    if (action === 'cancel') {
      closeApiEditorSilently(editor.tabName)
    }
  }
}

async function closeApiEditorFromPage(editor: ApiEditor) {
  await requestCloseApiEditor(editor)
}

async function deleteApi(row: any) {
  try {
    await confirmAction('确认删除该接口吗？', '删除接口', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/apis/${row.id}`)
    message.success('接口已删除')
    await refreshApisAfterDelete()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '接口删除失败')
  }
}

function resetCaseForm() {
  caseForm.id = undefined
  caseForm.project_id = undefined
  caseForm.api_id = undefined
  caseForm.name = ''
  caseForm.description = ''
  caseForm.bodyText = '{}'
  caseForm.bodyFormat = 'json'
  caseForm.assertionRows = []
  caseForm.extractorRows = []
}

function openCreateCasePage() {
  resetCaseForm()
  openRuntimeTab({ name: 'case-create', label: '新增用例', closable: true })
}

function openEditCasePage(row: any) {
  caseForm.id = row.id
  caseForm.project_id = row.project_id
  caseForm.api_id = row.api_id
  caseForm.name = row.name || ''
  caseForm.description = row.tags || ''
  caseForm.bodyFormat = bodyFormatFromApi(apis.value.find(item => item.id === row.api_id))
  caseForm.bodyText = caseForm.bodyFormat === 'xml'
    ? String(row.request_body ?? '')
    : JSON.stringify(row.request_body ?? {}, null, 2)
  caseForm.assertionRows = caseAssertionsToRows(row.assertions)
  caseForm.extractorRows = caseExtractorsToRows(row.extractors)
  openRuntimeTab({ name: `case-edit-${row.id}`, label: '编辑用例', closable: true })
}

function copyCase(row: any) {
  resetCaseForm()
  caseForm.project_id = row.project_id
  caseForm.api_id = row.api_id
  caseForm.name = `${row.name || '用例'} - 副本`
  caseForm.description = row.tags || ''
  caseForm.bodyFormat = bodyFormatFromApi(apis.value.find(item => item.id === row.api_id))
  caseForm.bodyText = caseForm.bodyFormat === 'xml'
    ? String(row.request_body ?? '')
    : JSON.stringify(row.request_body ?? {}, null, 2)
  caseForm.assertionRows = caseAssertionsToRows(row.assertions)
  caseForm.extractorRows = caseExtractorsToRows(row.extractors)
  openRuntimeTab({ name: 'case-create', label: '新增用例', closable: true })
}

function closeCaseEditorPage() {
  const target = active.value
  resetCaseForm()
  removeTab(target)
}

function changeCaseFormProject() {
  caseForm.api_id = undefined
  caseForm.bodyFormat = 'json'
}

function changeCaseFormApi() {
  syncCaseBodyFormatFromApi(true)
}

function caseAssertionsToRows(assertions: any[]): CaseAssertionRow[] {
  if (!Array.isArray(assertions)) {
    return []
  }
  return assertions.map(item => nextCaseAssertionRow(
    item?.type || 'status_code',
    item?.path || '',
    String(item?.expected ?? '')
  ))
}

function caseExtractorsToRows(extractors: any[]): CaseExtractorRow[] {
  if (!Array.isArray(extractors)) {
    return []
  }
  return extractors.map(item => {
    const source = ['jsonpath', 'xmlpath', 'regex'].includes(item?.source) ? item.source : 'jsonpath'
    return nextCaseExtractorRow(item?.name || '', item?.path || '', source)
  })
}

function caseAssertionRowsToPayload() {
  return caseForm.assertionRows
    .filter(row => row.target && row.check)
    .map(row => ({
      type: assertionTypeFromParts(row.target, row.check),
      path: assertionNeedsPath(row.target) ? row.path.trim() : '',
      expected: parseAssertionExpected(row.expected)
    }))
}

function assertionCheckOptions(target: AssertionTarget) {
  return assertionChecks[target] || assertionChecks.status
}

function assertionNeedsPath(target: AssertionTarget) {
  return ['jsonpath', 'xmlpath'].includes(target)
}

function assertionPathPlaceholder(target: AssertionTarget) {
  if (target === 'jsonpath') return '$.data.id'
  if (target === 'xmlpath') return './/STATUS'
  return '无需填写'
}

function changeCaseAssertionTarget(row: CaseAssertionRow) {
  row.check = defaultAssertionCheck(row.target)
  row.type = assertionTypeFromParts(row.target, row.check)
  row.path = assertionNeedsPath(row.target) ? row.path : ''
  row.expected = defaultAssertionExpected(row.target, row.check)
}

function syncCaseAssertionType(row: CaseAssertionRow) {
  row.type = assertionTypeFromParts(row.target, row.check)
  row.expected = defaultAssertionExpected(row.target, row.check)
}

function isNumericAssertion(target: AssertionTarget) {
  return ['status', 'duration'].includes(target)
}

function assertionExpectedPlaceholder(target: AssertionTarget) {
  if (target === 'status') return '必填数字，例如 200'
  if (target === 'duration') return '必填毫秒数，例如 1000'
  if (target === 'text') return 'success'
  return '200 / success'
}

function validateAssertionRows() {
  for (const row of caseForm.assertionRows) {
    if (!row.target || !isNumericAssertion(row.target)) {
      continue
    }
    const value = String(row.expected ?? '').trim()
    if (!/^\d+$/.test(value)) {
      message.warning(`${assertionTargets.find(item => item.value === row.target)?.label || '数字断言'}的期望值必须填写数字`)
      return false
    }
  }
  return true
}

function caseExtractorRowsToPayload() {
  return caseForm.extractorRows
    .map(row => ({ name: row.name.trim(), path: row.path.trim(), source: row.source }))
    .filter(row => row.name && row.path)
}

function caseExtractorPlaceholder(source: CaseExtractorRow['source']) {
  if (source === 'xmlpath') return './/STATUS'
  if (source === 'regex') return 'token=(\\w+)'
  return '$.data.token'
}

function parseAssertionExpected(value: string | number | null) {
  const trimmed = String(value ?? '').trim()
  if (!trimmed) {
    return ''
  }
  try {
    return JSON.parse(trimmed)
  } catch {
    return trimmed
  }
}

function addCaseAssertionRow() {
  caseForm.assertionRows.push(nextCaseAssertionRow())
}

function removeCaseAssertionRow(index: number) {
  caseForm.assertionRows.splice(index, 1)
}

function addCaseExtractorRow() {
  caseForm.extractorRows.push(nextCaseExtractorRow())
}

function removeCaseExtractorRow(index: number) {
  caseForm.extractorRows.splice(index, 1)
}

function validateCaseForm() {
  if (!caseForm.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!caseForm.api_id) {
    message.warning('请选择接口')
    return null
  }
  const name = caseForm.name.trim()
  if (!name) {
    message.warning('请输入用例名称')
    return null
  }
  if (!validateAssertionRows()) {
    return null
  }
  let requestBody: any = caseForm.bodyText
  if (caseForm.bodyFormat !== 'xml') {
    requestBody = parseJsonAllowVariables(caseForm.bodyText, undefined)
    if (requestBody === undefined) {
      message.warning(caseForm.bodyFormat === 'x-www-form-data' ? '表单 Body 必须是合法 JSON 对象' : 'Body 必须是合法 JSON')
      return null
    }
    if (caseForm.bodyFormat === 'x-www-form-data' && (!requestBody || typeof requestBody !== 'object' || Array.isArray(requestBody))) {
      message.warning('表单 Body 必须是 JSON 对象')
      return null
    }
  }
  return {
    project_id: caseForm.project_id,
    api_id: caseForm.api_id,
    name,
    request_headers: {},
    request_query: {},
    request_body: requestBody,
    assertions: caseAssertionRowsToPayload(),
    extractors: caseExtractorRowsToPayload(),
    tags: caseForm.description.trim(),
  }
}

function openCaseBodyDialog(row: any) {
  caseBodyPreview.value = JSON.stringify(row.request_body ?? {}, null, 2)
  caseBodyDialogVisible.value = true
}

async function saveCase() {
  const payload = validateCaseForm()
  if (!payload) {
    return
  }
  try {
    if (caseForm.id) {
      await api.put(`/cases/${caseForm.id}`, payload)
      message.success('用例已更新')
    } else {
      await api.post('/cases', payload)
      message.success('用例已创建')
    }
    caseSearch.project_id = payload.project_id
    caseSearch.api_id = payload.api_id
    resetCaseForm()
    await loadCases()
    await refreshAllCases()
    closeCaseEditorPage()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '用例保存失败')
  }
}

async function deleteCase(row: any) {
  try {
    await confirmAction('确认删除该用例吗？', '删除用例', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/cases/${row.id}`)
    message.success('用例已删除')
    await loadCases()
    if (caseList.value.length === 0 && casePagination.page > 1) {
      casePagination.page -= 1
      await loadCases()
    }
    await refreshAllCases()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '用例删除失败')
  }
}

function createEmptyPlanEditor(): PlanEditor {
  return {
    tabName: 'plan-create',
    label: '新增测试计划',
    mode: 'create',
    project_id: undefined,
    environment_id: undefined,
    api_id: undefined,
    name: '',
    candidateCases: [],
    selectedCases: [],
    queue: [],
    dirty: false
  }
}

function createEditPlanEditor(row: any): PlanEditor {
  return {
    tabName: `plan-edit-${row.id}`,
    label: '编辑测试计划',
    mode: 'edit',
    planId: row.id,
    project_id: row.project_id,
    environment_id: row.environment_id,
    api_id: row.api_id,
    name: row.name || '',
    candidateCases: [],
    selectedCases: [],
    queue: (row.cases || []).map((item: any) => normalizePlanQueueItem(item, row.environment_id)),
    dirty: false
  }
}

function openCreatePlanPage() {
  if (!planEditors['plan-create']) {
    planEditors['plan-create'] = createEmptyPlanEditor()
  }
  openRuntimeTab({ name: 'plan-create', label: '新增测试计划', closable: true })
}

function openEditPlanPage(row: any) {
  const tabName = `plan-edit-${row.id}`
  if (!planEditors[tabName]) {
    planEditors[tabName] = createEditPlanEditor(row)
  }
  openRuntimeTab({ name: tabName, label: '编辑测试计划', closable: true })
}

function markPlanEditorDirty(editor: PlanEditor) {
  editor.dirty = true
}

function normalizePlanQueueItem(item: any, defaultEnvironmentId?: number) {
  return {
    ...item,
    environment_id: item.environment_id || defaultEnvironmentId
  }
}

function planEditorEnvironments(editor: PlanEditor) {
  return environments.value.filter(item => editor.project_id && item.project_id === editor.project_id)
}

function planEditorApis(editor: PlanEditor) {
  return apis.value.filter(item => editor.project_id && item.project_id === editor.project_id)
}

function changePlanEditorProject(editor: PlanEditor) {
  editor.environment_id = undefined
  editor.api_id = undefined
  editor.candidateCases = []
  editor.selectedCases = []
  editor.queue = []
  markPlanEditorDirty(editor)
}

function changePlanEditorDefaultEnvironment(editor: PlanEditor) {
  editor.queue.forEach(item => {
    if (!item.environment_id) {
      item.environment_id = editor.environment_id
    }
  })
  markPlanEditorDirty(editor)
}

function changePlanEditorApi(editor: PlanEditor) {
  editor.candidateCases = []
  editor.selectedCases = []
  markPlanEditorDirty(editor)
}

function planNameExists(projectId: number, name: string, planId?: number) {
  return planList.value.some(item =>
    item.project_id === projectId &&
    item.name === name &&
    item.id !== planId
  )
}

function validatePlanEditor(editor: PlanEditor) {
  if (!editor.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!editor.environment_id) {
    message.warning('请选择环境')
    return null
  }
  if (!editor.api_id) {
    message.warning('请选择接口')
    return null
  }
  const name = editor.name.trim()
  if (!name) {
    message.warning('请输入测试计划名称')
    return null
  }
  if (planNameExists(editor.project_id, name, editor.planId)) {
    message.warning('测试计划名称已存在')
    return null
  }
  if (editor.queue.length === 0) {
    message.warning('请至少添加一条测试用例')
    return null
  }
  if (editor.queue.some(item => !item.environment_id)) {
    message.warning('请为执行队列中的每条用例选择环境')
    return null
  }
  return {
    project_id: editor.project_id,
    environment_id: editor.environment_id,
    api_id: editor.api_id,
    name,
    items: editor.queue.map(item => ({ case_id: item.id, environment_id: item.environment_id }))
  }
}

async function loadPlanCandidateCases(editor: PlanEditor) {
  if (!editor.project_id || !editor.environment_id || !editor.api_id) {
    message.warning('请先选择项目、环境和接口')
    return
  }
  const { data } = await api.get('/cases', {
    params: {
      project_id: editor.project_id,
      api_id: editor.api_id
    }
  })
  editor.candidateCases = data
  editor.selectedCases = []
}

function changePlanCandidateSelection(editor: PlanEditor, rows: any[]) {
  editor.selectedCases = rows
}

function addSelectedPlanCases(editor: PlanEditor) {
  const exists = new Set(editor.queue.map(item => item.id))
  editor.selectedCases.forEach(item => {
    if (!exists.has(item.id)) {
      editor.queue.push(normalizePlanQueueItem(item, editor.environment_id))
      exists.add(item.id)
    }
  })
  markPlanEditorDirty(editor)
}

function removePlanQueueCase(editor: PlanEditor, index: number) {
  editor.queue.splice(index, 1)
  markPlanEditorDirty(editor)
}

function startPlanQueueDrag(editor: PlanEditor, index: number) {
  editor.dragIndex = index
}

function dropPlanQueueRow(editor: PlanEditor, index: number) {
  const from = editor.dragIndex
  editor.dragIndex = undefined
  if (from === undefined || from === index) {
    return
  }
  const [row] = editor.queue.splice(from, 1)
  editor.queue.splice(index, 0, row)
  markPlanEditorDirty(editor)
}

async function savePlanEditor(editor: PlanEditor, closeAfterSave = false) {
  const payload = validatePlanEditor(editor)
  if (!payload) {
    return false
  }
  try {
    if (editor.mode === 'edit') {
      await api.put(`/plans/${editor.planId}`, payload)
      message.success('测试计划已更新')
      markSavedPlanEdited(editor)
    } else {
      const { data } = await api.post('/plans', payload)
      message.success('测试计划已创建')
      if (!closeAfterSave) {
        promoteCreatedPlanEditor(editor, data.id)
      }
    }
    editor.dirty = false
    planSearch.project_id = payload.project_id
    planSearch.api_id = payload.api_id
    await refreshPlansAfterChange()
    if (closeAfterSave) {
      closePlanEditorSilently(editor.tabName)
    }
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '测试计划保存失败')
    return false
  }
}

function promoteCreatedPlanEditor(editor: PlanEditor, planId: number) {
  const oldTabName = editor.tabName
  const newTabName = `plan-edit-${planId}`
  delete planEditors[oldTabName]
  editor.tabName = newTabName
  editor.label = '编辑测试计划'
  editor.mode = 'edit'
  editor.planId = planId
  planEditors[newTabName] = editor
  const tab = openedTabs.value.find(item => item.name === oldTabName)
  if (tab) {
    tab.name = newTabName
    tab.label = editor.label
  }
  active.value = newTabName
  saveTabs()
}

function closePlanEditorSilently(tabName: string) {
  delete planEditors[tabName]
  removeTab(tabName)
}

async function requestClosePlanEditor(editor: PlanEditor) {
  if (!editor.dirty) {
    closePlanEditorSilently(editor.tabName)
    return
  }
  try {
    await confirmAction('当前测试计划内容尚未保存，是否保存后关闭？', '关闭测试计划', {
      confirmButtonText: '保存并关闭',
      cancelButtonText: '不保存关闭',
      distinguishCancelAndClose: true,
      type: 'warning'
    })
    await savePlanEditor(editor, true)
  } catch (action) {
    if (action === 'cancel') {
      closePlanEditorSilently(editor.tabName)
    }
  }
}

async function closePlanEditorFromPage(editor: PlanEditor) {
  await requestClosePlanEditor(editor)
}

async function deletePlan(row: any) {
  try {
    await confirmAction('确认删除该测试计划吗？', '删除测试计划', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/plans/${row.id}`)
  message.success('测试计划已删除')
  await loadPlans()
}

function clearPlanExecutionPoller(planId: number) {
  const timer = planExecutionPollers.get(planId)
  if (timer) {
    window.clearInterval(timer)
    planExecutionPollers.delete(planId)
  }
}

function updatePlanExecutionState(planId: number, taskId: number, status: string, row?: any, results: any[] = []) {
  const resultStatusMap = new Map(results.filter(item => item?.case_id).map(item => [item.case_id, item.status]))
  const fallbackStatus = fallbackExecutionCaseStatus(status, results)
  const plans = [row, planList.value.find(item => item.id === planId)].filter((item, index, items) => item && items.indexOf(item) === index)

  for (const plan of plans) {
    plan.last_execution_id = taskId
    plan.last_status = status
    for (const caseRow of plan.cases || []) {
      caseRow.status = resultStatusMap.get(caseRow.id) || fallbackStatus
    }
  }
  syncExecutionDetail(planId, taskId, status, row, results)
}

function initialPlanExecutionResults(row: any, status = 'queued') {
  return (row?.cases || []).map((caseRow: any) => ({
    id: `pending-${caseRow.id}`,
    case_id: caseRow.id,
    case_name: caseRow.name || '',
    api_name: caseRow.api_name || '',
    status,
    request_snapshot: {},
    response_snapshot: {},
    assertion_results: [],
    duration_ms: 0,
    error_message: '',
  }))
}

function mergePlanExecutionResults(row: any, results: any[], fallbackStatus: string) {
  const resultMap = new Map((results || []).filter(item => item?.case_id).map(item => [item.case_id, item]))
  return (row?.cases || []).map((caseRow: any) => resultMap.get(caseRow.id) || {
    id: `pending-${caseRow.id}`,
    case_id: caseRow.id,
    case_name: caseRow.name || '',
    api_name: caseRow.api_name || '',
    status: fallbackStatus,
    request_snapshot: {},
    response_snapshot: {},
    assertion_results: [],
    duration_ms: 0,
    error_message: '',
  })
}

function fallbackExecutionCaseStatus(status: string, results: any[] = []) {
  if (['queued', 'running'].includes(status)) return status
  if (!results.length && ['passed', 'failed', 'error'].includes(status)) return status
  return ''
}

function resetExecutionDetailForPlan(row: any, taskId: number, status = 'queued') {
  executionDetail.task = {
    id: taskId,
    target_name: row?.name || '',
    status,
    summary: {}
  }
  executionDetail.results = initialPlanExecutionResults(row, status)
  executionDetailDialogVisible.value = true
}

function syncExecutionDetail(planId: number, taskId: number, status: string, row?: any, results: any[] = []) {
  if (!executionDetailDialogVisible.value || executionDetail.task?.id !== taskId) {
    return
  }
  const plan = row || planList.value.find(item => item.id === planId)
  executionDetail.task = {
    ...(executionDetail.task || {}),
    id: taskId,
    target_name: plan?.name || executionDetail.task?.target_name || '',
    status,
  }
  const fallbackStatus = fallbackExecutionCaseStatus(status, results)
  executionDetail.results = mergePlanExecutionResults(plan, results, fallbackStatus)
}

async function refreshExecutionViews() {
  await Promise.all([
    loadReports(),
    loadUiReports(),
    api.get('/executions').then(r => executions.value = r.data)
  ])
}

function pollPlanExecution(planId: number, taskId: number, row?: any) {
  clearPlanExecutionPoller(planId)
  let attempts = 0
  let polling = false
  const terminalStatuses = new Set(['passed', 'failed', 'error'])
  const poll = async () => {
    if (polling) return
    polling = true
    attempts += 1
    try {
      const { data } = await api.get(`/executions/${taskId}`, { headers: { 'X-Session-Activity': '0' } })
      const status = data?.task?.status || ''
      if (status) {
        updatePlanExecutionState(planId, taskId, status, row, data?.results || [])
        if (executionDetailDialogVisible.value && executionDetail.task?.id === taskId) {
          executionDetail.task = data.task
          syncExecutionDetail(planId, taskId, status, row, data?.results || [])
        }
      }
      if (attempts >= 30 && !terminalStatuses.has(status)) {
        await api.post(`/executions/${taskId}/timeout`)
        updatePlanExecutionState(planId, taskId, 'failed', row, data?.results || [])
        if (executionDetailDialogVisible.value && executionDetail.task?.id === taskId) {
          executionDetail.task = { ...(data.task || executionDetail.task || {}), status: 'failed', summary: { ...(data.task?.summary || {}), error: '执行超时' } }
          syncExecutionDetail(planId, taskId, 'failed', row, data?.results || [])
        }
      }
      if (terminalStatuses.has(status) || attempts >= 30) {
        clearPlanExecutionPoller(planId)
        await Promise.all([loadPlans(), refreshExecutionViews()])
      }
    } catch {
      if (attempts >= 30) {
        await api.post(`/executions/${taskId}/timeout`).catch(() => {})
        updatePlanExecutionState(planId, taskId, 'failed', row)
        clearPlanExecutionPoller(planId)
        await Promise.all([loadPlans(), refreshExecutionViews()])
      }
    } finally {
      polling = false
    }
  }
  const timer = window.setInterval(poll, 1000)
  planExecutionPollers.set(planId, timer)
  void poll()
}

async function submitPlanExecution(row: any, openDetail = true) {
  clearPlanExecutionPoller(row.id)
  const { data } = await api.post(`/plans/${row.id}/execute`)
  const taskId = data.id
  const status = data.status || 'queued'
  if (openDetail) {
    resetExecutionDetailForPlan(row, taskId, status)
  }
  updatePlanExecutionState(row.id, taskId, status, row)
  pollPlanExecution(row.id, taskId, row)
  return { taskId, status }
}

async function executePlan(row: any) {
  await submitPlanExecution(row, true)
  message.success('执行任务已提交')
  await refreshExecutionViews()
}

async function executeSelectedPlans() {
  const selectedRows = planList.value.filter(item => selectedPlanIds.value.includes(item.id))
  if (!selectedRows.length) {
    message.warning('请先选择要执行的测试计划')
    return
  }
  try {
    await confirmAction(`确认批量执行选中的 ${selectedRows.length} 个测试计划吗？`, '批量执行测试计划', {
      confirmButtonText: '执行',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  batchExecutingPlans.value = true
  const results = await Promise.allSettled(selectedRows.map(row => submitPlanExecution(row, false)))
  batchExecutingPlans.value = false
  const successCount = results.filter(item => item.status === 'fulfilled').length
  const failedCount = results.length - successCount
  selectedPlanIds.value = []
  if (successCount) {
    message.success(`已提交 ${successCount} 个测试计划执行任务${failedCount ? `，${failedCount} 个提交失败` : ''}`)
  } else {
    message.error('批量执行提交失败')
  }
  await refreshExecutionViews()
}

function findCaseApi(row: any) {
  return apis.value.find(item => item.id === row.api_id)
}

function findCaseEnvironment(row: any, environmentId?: number) {
  const apiRow = findCaseApi(row)
  return environments.value.find(item => item.id === environmentId) ||
    environments.value.find(item => apiRow?.environment_id && item.id === apiRow.environment_id)
}

function buildFullRequestUrl(environment: any, apiRow: any, query: Record<string, any>) {
  if (!apiRow) {
    return ''
  }
  const baseUrl = String(environment?.base_url || '').trim().replace(/\/+$/, '')
  const protocol = environment?.protocol || 'http'
  const defaultPort = protocol === 'http' ? 80 : 443
  const port = environment?.port && Number(environment.port) !== defaultPort ? `:${environment.port}` : ''
  const root = /^https?:\/\//i.test(baseUrl) ? baseUrl : `${protocol}://${baseUrl.replace(/^\/+/, '')}${port}`
  const path = String(apiRow.path || '').replace(/^\/+/, '')
  const url = `${root}/${path}`
  const queryText = new URLSearchParams(
    Object.entries(query || {}).reduce<Record<string, string>>((result, [key, value]) => {
      if (key.trim()) {
        result[key] = String(value ?? '')
      }
      return result
    }, {})
  ).toString()
  return queryText ? `${url}?${queryText}` : url
}

async function openCaseDetailDialog(row: any, environmentId?: number, executionId?: number) {
  const apiRow = apis.value.find(item => item.id === row.api_id)
  const environment = findCaseEnvironment(row, environmentId)
  const requestQuery = { ...(apiRow?.query || {}), ...(row.request_query || {}) }
  const requestHeaders = { ...(environment?.headers || {}), ...(apiRow?.headers || {}), ...(row.request_headers || {}) }
  let responseSnapshot: any = {}
  let requestSnapshot: any = {}
  if (executionId && row.id) {
    try {
      const { data } = await api.get(`/executions/${executionId}`)
      const result = (data.results || []).find((item: any) => item.case_id === row.id)
      responseSnapshot = result?.response_snapshot || {}
      requestSnapshot = result?.request_snapshot || {}
    } catch {}
  }
  Object.keys(caseDetail).forEach(key => delete caseDetail[key])
  Object.assign(caseDetail, {
    method: row.method || apiRow?.method || '',
    url: buildFullRequestUrl(environment, apiRow || row, requestQuery),
    body_format: row.body_format || bodyFormatFromApi(apiRow),
    request_headers: requestHeaders,
    request_body: requestSnapshot.body ?? row.request_body ?? {},
    request_body_original: requestSnapshot.body_original,
    sm3_signature: requestSnapshot.sm3_signature,
    assertions: row.assertions || [],
    extractors: row.extractors || [],
    extracted_variables: responseSnapshot.extracted_variables || [],
    response_snapshot: responseSnapshot
  })
  caseDetailDialogVisible.value = true
}

function formatJson(value: any) {
  return JSON.stringify(value ?? {}, null, 2)
}

function formatPayloadForDisplay(value: any, preferredFormat?: string) {
  if (value === undefined || value === null || value === '') return ''
  if (typeof value !== 'string') return formatJson(value)
  const text = value.trim()
  if (!text) return ''
  if (preferredFormat === 'xml' || text.startsWith('<')) {
    return formatXmlPayloadText(text)
  }
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

function formatResponseSnapshotBody(snapshot: any, preferredFormat?: string) {
  if (!snapshot || Object.keys(snapshot).length === 0) return ''
  if (snapshot.decrypted_text !== undefined) {
    return formatPayloadForDisplay(snapshot.decrypted_text, preferredFormat)
  }
  if (snapshot.text !== undefined && snapshot.text !== '') {
    return formatPayloadForDisplay(snapshot.text, preferredFormat)
  }
  if (snapshot.body !== undefined && snapshot.body !== '') {
    return formatPayloadForDisplay(snapshot.body, preferredFormat)
  }
  if (snapshot.json !== undefined && snapshot.json !== null) {
    return formatPayloadForDisplay(snapshot.json, 'json')
  }
  return formatJson(snapshot)
}

function formatMinute(value: string) {
  return value ? value.slice(0, 16) : ''
}

function markSavedPlanEdited(editor: PlanEditor) {
  if (!editor.planId) return
  const target = planList.value.find(item => item.id === editor.planId)
  if (!target) return
  target.last_status = 'edited'
  target.last_executed_at = ''
  target.last_execution_id = undefined
}

function planEnvironmentName(plan: any, environmentId?: number) {
  if (!environmentId || environmentId === plan?.environment_id) {
    return plan?.environment_name || ''
  }
  return environments.value.find(item => item.id === environmentId)?.name || ''
}

function executionStatusColor(status: string) {
  if (status === 'passed') return 'success'
  if (status === 'failed' || status === 'error') return 'error'
  if (status === 'stopped') return 'default'
  if (status === 'running') return 'warning'
  if (status === 'queued') return 'processing'
  if (status === 'edited') return 'warning'
  return 'default'
}

function executionStatusText(status: string) {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '执行中',
    passed: '已通过',
    failed: '失败',
    error: '异常',
    stopped: '已停止',
    edited: '已编辑'
  }
  return labels[status] || '未执行'
}

async function openExecutionDetail(row: any) {
  if (!row.last_execution_id) {
    message.warning('该测试计划暂无执行记录')
    return
  }
  const { data } = await api.get(`/executions/${row.last_execution_id}`)
  executionDetail.task = data.task
  executionDetail.results = mergePlanExecutionResults(row, data.results || [], fallbackExecutionCaseStatus(data.task?.status, data.results || []))
  executionDetailDialogVisible.value = true
  if (['queued', 'running'].includes(data.task?.status)) {
    pollPlanExecution(row.id, row.last_execution_id, row)
  }
}

async function openReport(row: any) {
  const reportWindow = window.open('', '_blank')
  if (!reportWindow) {
    message.warning('浏览器已拦截报告窗口，请允许弹窗后重试')
    return
  }
  reportWindow.document.write('<p style="font-family: Arial, sans-serif; padding: 24px;">报告加载中...</p>')
  try {
    const { data } = await api.get(`/executions/${row.id}/report`, { responseType: 'text' })
    reportWindow.document.open()
    reportWindow.document.write(data || '<h1>报告尚未生成</h1>')
    reportWindow.document.close()
  } catch (error: any) {
    reportWindow.document.open()
    reportWindow.document.write('<h1>报告加载失败</h1><p>请确认报告存在且当前账号仍处于登录状态。</p>')
    reportWindow.document.close()
    message.error(error?.response?.data?.detail || '报告加载失败')
  }
}

async function exportReport(row: any) {
  try {
    const { data } = await api.get(`/executions/${row.id}/report`, { responseType: 'text' })
    downloadHtmlReport(safeReportFilename(row.target_name || `测试报告_${row.id}`), data)
    message.success('报告已导出')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '报告导出失败')
  }
}

async function deleteReport(row: any) {
  try {
    await confirmAction('确认删除该报告吗？删除后报告中心将不再展示。', '删除报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteReportsByIds([row.id])
  message.success('报告已删除')
  await loadReports()
}

async function deleteSelectedReports() {
  const ids = [...selectedReportIds.value]
  if (!ids.length) {
    message.warning('请先选择要删除的报告')
    return
  }
  try {
    await confirmAction(`确认删除选中的 ${ids.length} 条报告吗？删除后报告中心将不再展示。`, '批量删除报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteReportsByIds(ids)
  selectedReportIds.value = []
  message.success('报告已批量删除')
  await loadReports()
}

async function deleteUiReport(row: any) {
  try {
    await confirmAction('确认删除该 UI 测试报告吗？删除后 UI 测试报告将不再展示。', '删除UI测试报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteReportsByIds([row.id])
  message.success('UI测试报告已删除')
  await loadUiReports()
}

async function deleteSelectedUiReports() {
  const ids = [...selectedUiReportIds.value]
  if (!ids.length) {
    message.warning('请先选择要删除的 UI 测试报告')
    return
  }
  try {
    await confirmAction(`确认删除选中的 ${ids.length} 条 UI 测试报告吗？删除后 UI 测试报告将不再展示。`, '批量删除UI测试报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteReportsByIds(ids)
  selectedUiReportIds.value = []
  message.success('UI测试报告已批量删除')
  await loadUiReports()
}

async function deleteReportsByIds(ids: number[]) {
  await Promise.all(ids.map(id => api.delete(`/executions/${id}`)))
}

async function runCase() {
  await api.post('/executions', { ...execForm, target_type: 'case' })
  message.success('执行任务已提交')
  await loadAll()
}

onMounted(async () => {
  window.addEventListener('session-expired', handleSessionExpired)
  try {
    const { data } = await api.get('/auth/me')
    me.value = data
    syncAllowedTabs()
    await loadAll()
  } catch {}
})

onUnmounted(() => {
  window.removeEventListener('session-expired', handleSessionExpired)
  Array.from(planExecutionPollers.keys()).forEach(clearPlanExecutionPoller)
  closeUiPicker(false)
  Object.values(uiArtifactObjectUrls).forEach(url => {
    if (url) URL.revokeObjectURL(url)
  })
  clearAiGenerationPoller()
})
</script>
